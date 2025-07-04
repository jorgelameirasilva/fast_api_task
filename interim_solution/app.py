import io
import json
import logging
import mimetypes
import os
import requests
import uuid
from pathlib import Path
from typing import AsyncGenerator

import aiohttp
import httpx

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import (
    DefaultAzureCredential,
    ClientSecretCredential,
    get_bearer_token_provider,
)

# Optional OpenTelemetry imports for monitoring
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    # OpenTelemetry not available - running in test mode
    configure_azure_monitor = None
    AioHttpClientInstrumentor = None
    OpenTelemetryMiddleware = None
    HTTPXClientInstrumentor = None
    OPENTELEMETRY_AVAILABLE = False

from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from openai import AsyncOpenAI, AsyncAzureOpenAI
from quart import (
    Blueprint,
    Quart,
    abort,
    current_app,
    jsonify,
    make_response,
    request,
    send_file,
    send_from_directory,
)

from quart_cors import cors

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.retrievethenread import RetrieveThenReadApproach
from core.authentication import AuthenticationHelper, token_required, AuthError
from core.identity import OneAccount
from core.logs import setup_logging
from services.cosmos_service import create_cosmos_service
from models.document import MessageCreateRequest, MessageContent, MessageVoteRequest

CONFIG_ASK_APPROACH = "ask_approach"
CONFIG_CHAT_APPROACH = "chat_approach"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_AUTH_CLIENT = "auth_client"
CONFIG_SEARCH_CLIENT = "search_client"
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_COSMOS_SERVICE = "cosmos_service"
ERROR_MESSAGE = """The app encountered an error processing your request.
If you are an administrator of the app, view the full error in the logs. See aka.ms/appservice-logs for more information.
Error type: {error_type}"""

ERROR_MESSAGE_FILTER = (
    """Your message contains content that was flagged by the OpenAI content filter."""
)

bp = Blueprint("routes", __name__, static_folder="static")
# Fix Windows registry issue with mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

bp = cors(bp, allow_origin="*", allow_methods=["GET", "POST"])

logger, listener, azure_handler = setup_logging("chatbot/chatbot-logs.log")


@bp.route("/")
async def index():
    return await send_from_directory("static", "index.html")


# Empty page is recommended for login redirect to work.
# See https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/initialization.md#redirect
@bp.route("/redirect")
async def redirect():
    return ""


@bp.route("/favicon.ico")
async def favicon():
    return await send_from_directory("static", "favicon.ico")


@bp.route("/assets/<path:path>")
async def assets(path):
    return await send_from_directory("static/assets", path)


# Serve content files from blob storage from within the app to keep the example self-contained.
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@bp.route("/content/<path:path>")
async def content_file(path: str):
    # Remove page number from path, filename-1.txt -> filename.txt
    if path.find("-page-") > 0:
        path_parts = path.rsplit("-page-", 1)
        path = path_parts[0]
    logging.info("Opening file %s", path)
    blob_container_client = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
    try:
        blob = blob_container_client.get_blob_client(f"chatbot/{path}").download_blob()
    except ResourceNotFoundError:
        logging.exception("Path not found: %s", path)
        abort(404)
    if not blob.properties or not blob.properties.has_key("content_settings"):
        abort(404)
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    blob_file = io.BytesIO()
    blob.readinto(blob_file)
    blob_file.seek(0)
    return await send_file(
        blob_file, mimetype=mime_type, as_attachment=False, attachment_filename=path
    )


def error_dict(error: Exception) -> dict:
    if hasattr(error, "status_code") and error.status_code == "content_filter":
        return {"error": ERROR_MESSAGE_FILTER}
    return {"error": ERROR_MESSAGE.format(error_type=error.__class__.__name__)}


def error_response(error: Exception, route: str, status_code: int = 500):
    logging.exception("Exception in %s: %s", route, error)
    if hasattr(error, "code") and error.code == "content_filter":
        status_code = 400
        return jsonify(error_dict(error)), status_code
    return jsonify(error_dict(error)), status_code


@bp.route("/ask", methods=["POST"])
@token_required
async def ask():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
    try:
        approach = current_app.config[CONFIG_ASK_APPROACH]
        r = await approach.run(
            request_json["messages"],
            context=context,
            session_state=request_json.get("session_state"),
        )
        return jsonify(r)
    except Exception as error:
        return error_response(error, "/ask")


async def format_as_ndjson(r: AsyncGenerator[dict, None]) -> AsyncGenerator[str, None]:
    try:
        async for event in r:
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except Exception as e:
        logging.exception("Exception while generating response stream: %s", e)
        yield json.dumps(error_dict(e))


@bp.route("/chat", methods=["POST"])
@token_required
async def chat():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    context = request_json.get("context", {})
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    context["auth_claims"] = await auth_helper.get_auth_claims_if_enabled(
        request.headers
    )

    # Get user info for session management
    cosmos_service = current_app.config[CONFIG_COSMOS_SERVICE]
    user_id = context["auth_claims"].get("oid", "anonymous_user")
    session_id = request_json.get("session_id")

    try:
        # Save user message to database if we have a session_id
        messages = request_json.get("messages", [])
        if messages and session_id:
            user_message = messages[-1]  # Get the latest user message
            if user_message.get("role") == "user":
                message_request = MessageCreateRequest(
                    session_id=session_id,
                    message=MessageContent(
                        role=user_message["role"], content=user_message["content"]
                    ),
                    knowledge_base=context.get("knowledge_base"),
                )
                await cosmos_service.create_message(message_request, user_id)
        elif messages and not session_id:
            # Create new session for first message
            session_id = str(uuid.uuid4())
            user_message = messages[-1]
            if user_message.get("role") == "user":
                message_request = MessageCreateRequest(
                    session_id=session_id,
                    message=MessageContent(
                        role=user_message["role"], content=user_message["content"]
                    ),
                    knowledge_base=context.get("knowledge_base"),
                )
                await cosmos_service.create_message(message_request, user_id)

        approach = current_app.config[CONFIG_CHAT_APPROACH]
        result = await approach.run(
            request_json["messages"],  # type: ignore
            stream=request_json.get("stream", False),
            context=context,
            session_state=request_json.get("session_state"),
        )

        # Save assistant response to database if we have session_id
        if session_id and isinstance(result, dict):
            # Extract assistant response
            choices = result.get("choices", [])
            if choices and choices[0].get("message"):
                assistant_message = choices[0]["message"]
                if assistant_message.get("role") == "assistant":
                    assistant_request = MessageCreateRequest(
                        session_id=session_id,
                        message=MessageContent(
                            role=assistant_message["role"],
                            content=assistant_message["content"],
                        ),
                        knowledge_base=context.get("knowledge_base"),
                    )
                    await cosmos_service.create_message(assistant_request, user_id)

            # Add session_id to response
            result["session_id"] = session_id

        if isinstance(result, dict):
            return jsonify(result)
        else:
            response = await make_response(format_as_ndjson(result))
            response.timeout = None  # type: ignore
            response.mimetype = "application/json-lines"
            return response
    except Exception as error:
        return error_response(error, "/chat")


@bp.route("/vote", methods=["POST"])
@token_required
async def vote():
    # Input validation for request
    if not request.is_json:
        return jsonify({"error": "Request must be json"}), 415

    # Get POST request
    request_json = await request.get_json()

    # Get user info and cosmos service
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
    cosmos_service = current_app.config[CONFIG_COSMOS_SERVICE]
    user_id = auth_claims.get("oid", "anonymous_user")

    user_query = request_json.get("user_query", {})
    chatbot_response = request_json.get("chatbot_response", {})
    count = request_json.get("count", {})
    upvote = request_json.get("upvote", {})
    downvote = request_json.get("downvote", {})
    message_id = request_json.get("message_id")  # New: message ID for database voting

    # Input validation for user_query and chatbot_response params
    if type(user_query) is str and user_query != {}:
        return (
            jsonify(
                {
                    "error": f"If user_query provided, it expects a string, but got {type(user_query)}"
                }
            ),
            415,
        )
    if type(chatbot_response) is str and chatbot_response != {}:
        return (
            jsonify(
                {
                    "error": f"If chatbot_response, it expects a string, but got {type(chatbot_response)}"
                }
            ),
            415,
        )
    elif type(chatbot_response) == str:
        chatbot_response = chatbot_response.strip().replace("\n", " ")

    # Input validation for upvote and downvote params
    if upvote not in [1, 0, {}]:
        return (
            jsonify(
                {
                    "error": f"Upvote must be either 1 or 0 (<<class 'int'>), but got {upvote} ({type(upvote)})"
                }
            ),
            400,
        )
    elif downvote not in [1, 0, {}]:
        return (
            jsonify(
                {
                    "error": f"Downvote must be either 1 or 0 (<<class 'int'>), but got {downvote} ({type(downvote)})"
                }
            ),
            400,
        )
    elif upvote == 1 and downvote == 1:
        return (
            jsonify(
                {"error": f"Both upvote and downvote were recorded simultaneously."}
            ),
            400,
        )
    elif upvote == 0 and downvote == 0:
        return (
            jsonify({"error": f"Neither an upvote nor a downvote were recorded."}),
            400,
        )

    # Input validation for count
    if count not in [-1, 1, {}]:
        return (
            jsonify({"error": f"Count must be either 1 or -1, but got {count}."}),
            400,
        )

    # Save vote to database if message_id is provided
    if message_id and upvote != {} and downvote != {}:
        try:
            # Get additional feedback for downvotes
            feedback = None
            if downvote == 1:
                reason_multiple_choice = request_json.get("reason_multiple_choice", "")
                additional_comments = request_json.get("additional_comments", "")
                if reason_multiple_choice or additional_comments:
                    feedback = f"Reason: {reason_multiple_choice}. Comments: {additional_comments}".strip()
            elif upvote == 1:
                feedback = request_json.get("feedback", "Helpful response")

            vote_request = MessageVoteRequest(
                message_id=message_id,
                upvote=upvote if upvote != {} else 0,
                downvote=downvote if downvote != {} else 0,
                feedback=feedback,
            )

            voted_message = await cosmos_service.vote_message(vote_request, user_id)
            if voted_message:
                logger.info(f"Vote saved to database for message {message_id}")
            else:
                logger.warning(f"Failed to save vote for message {message_id}")

        except Exception as e:
            logger.error(f"Error saving vote to database: {e}")

    # Record upvote (original logging logic)
    if upvote == 1:
        if count == 1:
            logger.info(
                "UPVOTE_RECORDED",
                extra={"user_query": user_query, "chatbot_response": chatbot_response},
            )
        elif count == -1:
            logger.info(
                "UPVOTE_REMOVED",
                extra={"user_query": user_query, "chatbot_response": chatbot_response},
            )

    # Record downvote (original logging logic)
    elif downvote == 1:
        reason_multiple_choice = request_json.get("reason_multiple_choice", {})
        if not isinstance(reason_multiple_choice, str):
            if reason_multiple_choice != {}:
                return (
                    jsonify(
                        {
                            "error": f"reason_multiple_choice must be a string, but got {type(reason_multiple_choice)}"
                        }
                    ),
                    400,
                )
        else:
            reason_multiple_choice = reason_multiple_choice.strip().replace("\n", " ")

        additional_comments = request_json.get("additional_comments", {})
        if not isinstance(additional_comments, str):
            if additional_comments != {}:
                return (
                    jsonify(
                        {
                            "error": f"additional_comments must be a string, but got {type(additional_comments)}"
                        }
                    ),
                    400,
                )
        else:
            additional_comments = additional_comments.strip().replace("\n", " ")

        if count == 1:
            logger.info(
                "DOWNVOTE_RECORDED",
                extra={
                    "user_query": user_query,
                    "chatbot_response": chatbot_response,
                    "reason_multiple_choice": reason_multiple_choice,
                    "additional_comments": additional_comments,
                },
            )
        elif count == -1:
            logger.info(
                "DOWNVOTE_REMOVED",
                extra={
                    "user_query": user_query,
                    "chatbot_response": chatbot_response,
                    "reason_multiple_choice": reason_multiple_choice,
                    "additional_comments": additional_comments,
                },
            )

    return (
        jsonify(
            {
                "user_query": user_query,
                "chatbot_response": chatbot_response,
                "upvote": upvote,
                "downvote": downvote,
                "count": count,
                "message_id": message_id,
                "saved_to_database": message_id is not None,
            }
        ),
        200,
    )


# Send MSAL.js settings to the client UI
@bp.route("/auth_setup", methods=["GET"])
def auth_setup():
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    return jsonify(auth_helper.get_auth_setup_for_client())


@bp.route("/sessions", methods=["GET"])
@token_required
async def get_user_sessions():
    """Get all sessions for the current user"""
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
    cosmos_service = current_app.config[CONFIG_COSMOS_SERVICE]
    user_id = auth_claims.get("oid", "anonymous_user")

    try:
        sessions = await cosmos_service.get_user_sessions(user_id, limit=50)
        return jsonify(
            {
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "title": session.title,
                        "message_count": session.message_count,
                        "created_at": session.created_at.isoformat(),
                        "updated_at": session.updated_at.isoformat(),
                    }
                    for session in sessions
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        return jsonify({"error": "Failed to get sessions"}), 500


@bp.route("/sessions/<session_id>/messages", methods=["GET"])
@token_required
async def get_session_messages(session_id: str):
    """Get all messages for a specific session"""
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
    cosmos_service = current_app.config[CONFIG_COSMOS_SERVICE]
    user_id = auth_claims.get("oid", "anonymous_user")

    try:
        messages = await cosmos_service.get_conversation(session_id, user_id)
        return jsonify(
            {
                "session_id": session_id,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.message.role,
                        "content": msg.message.content,
                        "created_at": msg.created_at.isoformat(),
                        "upvote": msg.upvote,
                        "downvote": msg.downvote,
                        "feedback": msg.feedback,
                    }
                    for msg in messages
                ],
            }
        )
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        return jsonify({"error": "Failed to get session messages"}), 500


@bp.route("/sessions/<session_id>", methods=["DELETE"])
@token_required
async def delete_session(session_id: str):
    """Delete a session and all its messages"""
    auth_helper = current_app.config[CONFIG_AUTH_CLIENT]
    auth_claims = await auth_helper.get_auth_claims_if_enabled(request.headers)
    cosmos_service = current_app.config[CONFIG_COSMOS_SERVICE]
    user_id = auth_claims.get("oid", "anonymous_user")

    try:
        success = await cosmos_service.delete_session(session_id, user_id)
        if success:
            return jsonify({"message": "Session deleted successfully"})
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({"error": "Failed to delete session"}), 500


@bp.before_app_serving
async def setup_clients():
    from dotenv import load_dotenv

    load_dotenv(".")

    AZURE_STORAGE_CLIENT_ID = os.environ.get("AZURE_STORAGE_CLIENT_ID")
    AZURE_STORAGE_CLIENT_SECRET = os.environ.get("AZURE_STORAGE_CLIENT_SECRET")

    # Replace usage with your own values, filter in environment variables or directly here
    AZURE_STORAGE_ACCOUNT = os.environ.get(
        "AZURE_STORAGE_ACCOUNT", "stdiagnosticsstorageprod"
    )
    AZURE_STORAGE_CONTAINER = os.environ.get(
        "DIAGNOSTICS_STORAGE_CONTAINER",
        "s-alt-0303-asia-or-us3-dlc13-webintelligentchatbot",
    )
    AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE")
    AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX")
    AZURE_SEARCH_CLIENT_ID = os.environ.get("AZURE_SEARCH_CLIENT_ID")
    AZURE_SEARCH_CLIENT_SECRET = os.environ.get("AZURE_SEARCH_CLIENT_SECRET")
    AZURE_SEARCH_TENANT_ID = os.environ.get("AZURE_SEARCH_TENANT_ID")
    OPENAI_HOST = os.environ.get("OPENAI_HOST", "azure")
    AZURE_OPENAI_CHATGPT_MODEL = os.environ.get("AZURE_OPENAI_CHATGPT_MODEL", "gpt-4o")
    AZURE_OPENAI_EMB_MODEL_NAME = os.environ.get(
        "AZURE_OPENAI_EMB_MODEL_NAME", "text-embedding-ada-002"
    )
    AZURE_OPENAI_SERVICE = os.environ.get(
        "AZURE_OPENAI_SERVICE", "saic-azu-eus2-npd-openaioc-specialservices"
    )
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = (
        os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o-chatbot-poc")
        if OPENAI_HOST == "azure"
        else None
    )
    AZURE_OPENAI_EMB_DEPLOYMENT = (
        os.environ.get("AZURE_OPENAI_EMB_DEPLOYMENT", "embeddings")
        if OPENAI_HOST == "azure"
        else None
    )

    openai_client = None
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_ORGANIZATION = os.environ.get("OPENAI_ORGANIZATION")
    AZURE_USE_AUTHENTICATION = (
        os.environ.get("AZURE_USE_AUTHENTICATION", "").lower() == "true"
    )
    AZURE_SERVER_APP_ID = os.environ.get("AZURE_SERVER_APP_ID")
    AZURE_SERVER_APP_SECRET = os.environ.get("AZURE_SERVER_APP_SECRET")
    AZURE_CLIENT_APP_ID = os.environ.get("AZURE_CLIENT_APP_ID")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
    TOKEN_CACHE_PATH = os.environ.get("TOKEN_CACHE_PATH")

    KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE", "sourcepage")

    AZURE_SEARCH_QUERY_LANGUAGE = os.environ.get("AZURE_SEARCH_QUERY_LANGUAGE", "en-us")
    AZURE_SEARCH_QUERY_SPELLER = os.environ.get("AZURE_SEARCH_QUERY_SPELLER", "lexicon")

    STORAGE_CONNECTION_STRING = os.environ.get("STORAGE_CONNECTION_STRING")
    SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY")

    SECURE_GPT_DEPLOYMENT_ID = os.environ.get("SECURE_GPT_DEPLOYMENT_ID")
    SECURE_GPT_EMB_DEPLOYMENT_ID = os.environ.get("SECURE_GPT_EMB_DEPLOYMENT_ID")
    SECURE_GPT_CLIENT_ID = os.environ.get("SECURE_GPT_CLIENT_ID")
    SECURE_GPT_CLIENT_SECRET = os.environ.get("SECURE_GPT_CLIENT_SECRET")
    APIM_KEY = os.environ.get("APIM_KEY")
    APIM_ONELOGIN_URL = os.environ.get("APIM_ONELOGIN_URL")
    WITH_BASE_URL = os.environ.get("APIM_BASE_URL")
    SECURE_GPT_API_VERSION = os.environ.get("SECURE_GPT_API_VERSION")

    AZURE_SEARCH_CLIENT_ID = os.environ.get("AZURE_SEARCH_CLIENT_ID")
    AZURE_SEARCH_CLIENT_SECRET = os.environ.get("AZURE_SEARCH_CLIENT_SECRET")
    AZURE_SEARCH_TENANT_ID = os.environ.get("AZURE_SEARCH_TENANT_ID")

    # Use the current user identity to authenticate with Azure OpenAI, AI Search and Blob Storage (no secrets needed,
    # just use "az login" locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the
    # keys for each service
    # If you encounter a blocking error during a DefaultAzureCredential resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
    azure_credential = DefaultAzureCredential(
        exclude_shared_token_cache_credential=True
    )

    # Set up clients for AI Search and Storage
    os.environ["AZURE_CLIENT_ID"] = AZURE_SEARCH_CLIENT_ID
    os.environ["AZURE_CLIENT_SECRET"] = AZURE_SEARCH_CLIENT_SECRET
    os.environ["AZURE_TENANT_ID"] = AZURE_SEARCH_TENANT_ID

    # Set up authentication helper
    auth_helper = AuthenticationHelper(
        use_authentication=AZURE_USE_AUTHENTICATION,
        server_app_id=AZURE_SERVER_APP_ID,
        server_app_secret=AZURE_SERVER_APP_SECRET,
        client_app_id=AZURE_CLIENT_APP_ID,
        tenant_id=AZURE_TENANT_ID,
        token_cache_path=TOKEN_CACHE_PATH,
    )

    # Initialize CosmosService for session and vote storage
    cosmos_service = create_cosmos_service()

    # Set up clients for AI Search and Storage
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=ClientSecretCredential(
            tenant_id=AZURE_SEARCH_TENANT_ID,
            client_id=AZURE_SEARCH_CLIENT_ID,
            client_secret=AZURE_SEARCH_CLIENT_SECRET,
        ),
    )
    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=ClientSecretCredential(
            client_id=AZURE_STORAGE_CLIENT_ID,
            client_secret=AZURE_STORAGE_CLIENT_SECRET,
            tenant_id=AZURE_SEARCH_TENANT_ID,
        ),
    )

    blob_container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

    # Used by the OpenAI SDK
    openai_client: AsyncOpenAI

    APIM_COMPLETIONS_URL = f"{WITH_BASE_URL}/{SECURE_GPT_DEPLOYMENT_ID}"
    APIM_EMBEDDINGS_URL = f"{WITH_BASE_URL}/{SECURE_GPT_EMB_DEPLOYMENT_ID}"

    openai_client = AsyncAzureOpenAI(
        base_url=APIM_COMPLETIONS_URL,
        azure_ad_token_provider=get_bearer_token_provider(
            OneAccount(
                SECURE_GPT_CLIENT_ID,
                SECURE_GPT_CLIENT_SECRET,
                APIM_KEY,
                APIM_ONELOGIN_URL,
            )
        ),
        api_version=SECURE_GPT_API_VERSION,
        http_client=httpx.AsyncClient(verify=False),
        default_headers={"Ocp-Apim-Subscription-Key": APIM_KEY},
    )

    embeddings_client = AsyncAzureOpenAI(
        base_url=APIM_EMBEDDINGS_URL,
        azure_ad_token_provider=get_bearer_token_provider(
            OneAccount(
                SECURE_GPT_CLIENT_ID,
                SECURE_GPT_CLIENT_SECRET,
                APIM_KEY,
                APIM_ONELOGIN_URL,
            )
        ),
        api_version=SECURE_GPT_API_VERSION,
        http_client=httpx.AsyncClient(verify=False),
        default_headers={"Ocp-Apim-Subscription-Key": APIM_KEY},
    )

    chatgpt_model = SECURE_GPT_DEPLOYMENT_ID
    embedding_model = SECURE_GPT_EMB_DEPLOYMENT_ID

    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_AUTH_CLIENT] = auth_helper

    # Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
    # or some derivative, here we include several for exploration purposes
    current_app.config[CONFIG_ASK_APPROACH] = RetrieveThenReadApproach(
        search_client=search_client,
        openai_client=openai_client,
        embeddings_client=embeddings_client,
        chatgpt_model=chatgpt_model,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=embedding_model,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
    )

    current_app.config[CONFIG_CHAT_APPROACH] = ChatReadRetrieveReadApproach(
        search_client=search_client,
        openai_client=openai_client,
        embeddings_client=embeddings_client,
        chatgpt_model=chatgpt_model,
        chatgpt_deployment=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        embedding_model=embedding_model,
        embedding_deployment=AZURE_OPENAI_EMB_DEPLOYMENT,
        sourcepage_field=KB_FIELDS_SOURCEPAGE,
        content_field=KB_FIELDS_CONTENT,
        query_language=AZURE_SEARCH_QUERY_LANGUAGE,
        query_speller=AZURE_SEARCH_QUERY_SPELLER,
    )

    current_app.config[CONFIG_COSMOS_SERVICE] = cosmos_service


@bp.after_app_serving
async def shutdown():
    listener.stop()
    azure_handler.close()


def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)

    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") and OPENTELEMETRY_AVAILABLE:
        configure_azure_monitor()
        # This tracks HTTP requests made by aiohttp:
        AioHttpClientInstrumentor().instrument()
        # This tracks HTTP requests made by httpx/openai:
        HTTPXClientInstrumentor().instrument()
        # This middleware tracks app route requests:
        app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)  # type: ignore[method-assign]

    # Level should be one of https://docs.python.org/3/library/logging.html#logging-levels
    default_level = "INFO"  # In development, log more verbosely
    if os.getenv("WEBSITE_HOSTNAME"):  # In production, don't log as heavily
        default_level = "WARNING"

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    if allowed_origin := os.getenv("ALLOWED_ORIGIN"):
        app.logger.info("CORS enabled for %s", allowed_origin)
        cors(app, allow_origin=allowed_origin, allow_methods=["GET", "POST"])
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
