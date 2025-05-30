"""
Tests for the setup system and client initialization.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.setup import (
    setup_clients,
    cleanup_clients,
    get_search_client,
    get_openai_client,
    get_blob_client,
    get_auth_helper,
    get_app_config,
    current_app_config,
    MockSearchClient,
    MockBlobClient,
    MockOpenAIClient,
    _setup_search_client,
    _setup_blob_client,
    _setup_openai_client,
    _setup_auth_helper,
    _setup_approaches,
)
from app.core.config import settings
from app.approaches.approach_registry import _approach_registry

# Check if Azure SDKs are available
try:
    import azure.search.documents
    import azure.storage.blob
    import azure.core.credentials

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class TestSetupSystem:
    """Test the main setup system functionality"""

    @pytest.fixture(autouse=True)
    def clear_config(self):
        """Clear global config before each test"""
        global current_app_config
        current_app_config.clear()
        # Clear registry pre-configured instances
        _approach_registry._preconfigured_instances.clear()
        # Clear cache for dependency injection functions
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()
        yield
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()

    @pytest.mark.asyncio
    async def test_setup_clients_basic_flow(self):
        """Test the basic setup flow with mock clients"""
        await setup_clients()

        # Verify clients are created and stored
        assert get_search_client() is not None
        assert get_openai_client() is not None
        assert get_blob_client() is not None

        # Verify they are mock clients (since no real config)
        assert isinstance(get_search_client(), MockSearchClient)
        assert isinstance(get_openai_client(), MockOpenAIClient)
        assert isinstance(get_blob_client(), MockBlobClient)

    @pytest.mark.asyncio
    async def test_approach_registration_after_setup(self):
        """Test that approaches are properly registered after setup"""
        await setup_clients()

        # Check that pre-configured instances are available
        assert _approach_registry.has_preconfigured_instances()

        # Test approach retrieval
        from app.approaches import get_approach

        retrieve_approach = get_approach("retrieve_then_read")
        chat_approach = get_approach("chat_read_retrieve_read")

        assert retrieve_approach is not None
        assert chat_approach is not None
        assert retrieve_approach.name == "RetrieveThenRead"
        assert chat_approach.name == "ChatReadRetrieveRead"

        # Verify they have the injected clients
        assert retrieve_approach.search_client is not None
        assert retrieve_approach.openai_client is not None
        assert chat_approach.search_client is not None
        assert chat_approach.openai_client is not None

    @pytest.mark.asyncio
    async def test_cleanup_clients(self):
        """Test the cleanup functionality"""
        await setup_clients()

        # Ensure clients exist
        assert get_search_client() is not None

        # Cleanup should not raise errors
        await cleanup_clients()

    @pytest.mark.asyncio
    async def test_get_app_config(self):
        """Test the app config getter"""
        await setup_clients()

        # Test existing keys
        search_client = get_app_config("search_client")
        assert search_client is not None

        # Test default value
        non_existent = get_app_config("non_existent", "default_value")
        assert non_existent == "default_value"


class TestClientSetup:
    """Test individual client setup functions"""

    @pytest.mark.asyncio
    async def test_search_client_mock_fallback(self):
        """Test search client falls back to mock when no config"""
        client = await _setup_search_client()
        assert isinstance(client, MockSearchClient)

    @pytest.mark.asyncio
    async def test_blob_client_mock_fallback(self):
        """Test blob client falls back to mock when no config"""
        client = await _setup_blob_client()
        assert isinstance(client, MockBlobClient)

    @pytest.mark.asyncio
    async def test_openai_client_mock_fallback(self):
        """Test OpenAI client falls back to mock when no config"""
        client = await _setup_openai_client()
        assert isinstance(client, MockOpenAIClient)

    @pytest.mark.asyncio
    async def test_auth_helper_disabled_by_default(self):
        """Test auth helper is None when authentication is disabled"""
        helper = await _setup_auth_helper()
        assert helper is None

    @pytest.mark.asyncio
    async def test_auth_helper_enabled(self):
        """Test auth helper is created when authentication is enabled"""
        # Patch the settings directly instead of relying on environment variable reload
        with patch.object(settings, "AZURE_USE_AUTHENTICATION", True), patch.object(
            settings, "AZURE_TENANT_ID", "test-tenant"
        ):

            helper = await _setup_auth_helper()
            assert helper is not None
            assert helper.use_authentication is True
            assert helper.tenant_id == "test-tenant"

    @pytest.mark.skipif(not AZURE_AVAILABLE, reason="Azure SDK not available")
    @pytest.mark.asyncio
    @patch("azure.search.documents.SearchClient")
    @patch("azure.core.credentials.AzureKeyCredential")
    async def test_search_client_real_setup(self, mock_credential, mock_search_client):
        """Test search client setup with real configuration"""
        with patch.object(
            settings, "AZURE_SEARCH_SERVICE", "test-search"
        ), patch.object(settings, "SEARCH_API_KEY", "test-key"), patch.object(
            settings, "AZURE_SEARCH_INDEX", "test-index"
        ):

            mock_client_instance = MagicMock()
            mock_search_client.return_value = mock_client_instance

            client = await _setup_search_client()

            # Should create real client, not mock
            assert client == mock_client_instance
            mock_search_client.assert_called_once()

    @pytest.mark.skipif(not AZURE_AVAILABLE, reason="Azure SDK not available")
    @pytest.mark.asyncio
    @patch("azure.storage.blob.BlobServiceClient")
    async def test_blob_client_real_setup(self, mock_blob_service):
        """Test blob client setup with real configuration"""
        with patch.object(
            settings, "AZURE_STORAGE_ACCOUNT", "test-storage"
        ), patch.object(
            settings,
            "STORAGE_CONNECTION_STRING",
            "DefaultEndpointsProtocol=https;AccountName=test;",
        ):

            mock_service_instance = MagicMock()
            mock_container_client = MagicMock()
            mock_service_instance.get_container_client.return_value = (
                mock_container_client
            )
            mock_blob_service.from_connection_string.return_value = (
                mock_service_instance
            )

            client = await _setup_blob_client()

            # Should create real client, not mock
            assert client == mock_container_client
            mock_blob_service.from_connection_string.assert_called_once()


class TestApproachSetup:
    """Test approach setup and registration"""

    @pytest.fixture(autouse=True)
    def clear_config(self):
        """Clear global config before each test"""
        global current_app_config
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        yield
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()

    @pytest.mark.asyncio
    async def test_setup_approaches(self):
        """Test approach setup and registration"""
        # Setup mock clients first
        from app.core.setup import MockSearchClient, MockOpenAIClient

        current_app_config["search_client"] = MockSearchClient()
        current_app_config["openai_client"] = MockOpenAIClient()

        # Set global clients for approach setup
        import app.core.setup as setup_module

        setup_module._search_client = current_app_config["search_client"]
        setup_module._openai_client = current_app_config["openai_client"]

        await _setup_approaches()

        # Verify approaches are registered
        assert _approach_registry.has_preconfigured_instances()

        # Test specific approaches
        from app.approaches import get_approach

        retrieve_approach = get_approach("retrieve_then_read")
        chat_approach = get_approach("chat_read_retrieve_read")

        assert retrieve_approach.search_client is not None
        assert retrieve_approach.openai_client is not None
        assert chat_approach.search_client is not None
        assert chat_approach.openai_client is not None

        # Test aliases work
        default_approach = get_approach("default")
        assert default_approach.name == "RetrieveThenRead"

    @pytest.mark.asyncio
    async def test_approach_configuration_parameters(self):
        """Test that approaches receive correct configuration parameters"""
        # Setup with mock clients
        current_app_config["search_client"] = MockSearchClient()
        current_app_config["openai_client"] = MockOpenAIClient()

        import app.core.setup as setup_module

        setup_module._search_client = current_app_config["search_client"]
        setup_module._openai_client = current_app_config["openai_client"]

        await _setup_approaches()

        from app.approaches import get_approach

        approach = get_approach("retrieve_then_read")

        # Verify configuration parameters are set correctly
        assert approach.chatgpt_model == settings.OPENAI_CHATGPT_MODEL
        assert approach.embedding_model == settings.OPENAI_EMB_MODEL
        assert approach.sourcepage_field == settings.KB_FIELDS_SOURCEPAGE
        assert approach.content_field == settings.KB_FIELDS_CONTENT


class TestMockClients:
    """Test mock client functionality"""

    @pytest.mark.asyncio
    async def test_mock_search_client(self):
        """Test mock search client functionality"""
        client = MockSearchClient()

        results = await client.search("test query")
        assert results == []

        # Should not raise error
        client.close()

    @pytest.mark.asyncio
    async def test_mock_blob_client(self):
        """Test mock blob client functionality"""
        client = MockBlobClient()

        blobs = await client.list_blobs()
        assert blobs == []

        # Should not raise error
        client.close()

    @pytest.mark.asyncio
    async def test_mock_openai_client(self):
        """Test mock OpenAI client functionality"""
        client = MockOpenAIClient()

        # Test chat completion
        chat_response = await client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": "test"}]
        )
        assert "choices" in chat_response
        assert chat_response["choices"][0]["message"]["content"] == "Mock response"

        # Test embeddings
        embedding_response = await client.embeddings.create(
            model="text-embedding-ada-002", input="test text"
        )
        assert "data" in embedding_response
        assert len(embedding_response["data"][0]["embedding"]) == 1536

        # Should not raise error
        client.close()


class TestErrorHandling:
    """Test error handling in setup system"""

    @pytest.fixture(autouse=True)
    def clear_config(self):
        """Clear global config before each test"""
        global current_app_config
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        # Clear cache for dependency injection functions
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()
        yield
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()

    @pytest.mark.asyncio
    async def test_individual_client_setup_handles_exceptions(self):
        """Test that individual client setups handle exceptions gracefully"""
        # Test by making the import fail (simulates missing dependencies)
        with patch("builtins.__import__", side_effect=ImportError("Test import error")):
            client = await _setup_search_client()
            assert isinstance(client, MockSearchClient)

    @pytest.mark.asyncio
    async def test_cleanup_clients_handles_exceptions(self):
        """Test that cleanup_clients handles exceptions gracefully"""
        await setup_clients()

        # Mock a client that raises an exception on close
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("Close error")

        import app.core.setup as setup_module

        setup_module._search_client = mock_client

        # Should not raise exception
        await cleanup_clients()

    @pytest.mark.asyncio
    async def test_approach_setup_failure_fallback(self):
        """Test that approach setup failures are handled gracefully"""
        # Setup clients first
        current_app_config["search_client"] = MockSearchClient()
        current_app_config["openai_client"] = MockOpenAIClient()

        import app.core.setup as setup_module

        setup_module._search_client = current_app_config["search_client"]
        setup_module._openai_client = current_app_config["openai_client"]

        # Mock approach class to fail
        with patch(
            "app.approaches.retrieve_then_read.RetrieveThenReadApproach",
            side_effect=Exception("Approach error"),
        ):
            # Should not raise exception
            await _setup_approaches()

            # Should still be able to get approaches (class-based fallback)
            from app.approaches import get_approach

            approach = get_approach("retrieve_then_read")
            assert approach is not None


class TestDependencyInjection:
    """Test dependency injection functionality"""

    @pytest.fixture(autouse=True)
    def clear_config(self):
        """Clear global config before each test"""
        global current_app_config
        current_app_config.clear()
        # Clear cache for dependency injection functions
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()
        yield
        current_app_config.clear()
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()

    @pytest.mark.asyncio
    async def test_dependency_injection_functions(self):
        """Test that dependency injection functions work correctly"""
        # Setup mock clients
        mock_search = MockSearchClient()
        mock_openai = MockOpenAIClient()
        mock_blob = MockBlobClient()

        current_app_config["search_client"] = mock_search
        current_app_config["openai_client"] = mock_openai
        current_app_config["blob_container_client"] = mock_blob
        current_app_config["auth_client"] = None

        # Test dependency injection
        assert get_search_client() == mock_search
        assert get_openai_client() == mock_openai
        assert get_blob_client() == mock_blob
        assert get_auth_helper() is None

    def test_dependency_injection_with_empty_config(self):
        """Test dependency injection when config is empty"""
        # Should return None for missing clients
        assert get_search_client() is None
        assert get_openai_client() is None
        assert get_blob_client() is None
        assert get_auth_helper() is None


class TestConfigurationProperties:
    """Test configuration property methods"""

    def test_azure_search_endpoint_property(self):
        """Test Azure search endpoint URL construction"""
        # Mock settings temporarily
        original_service = settings.AZURE_SEARCH_SERVICE
        settings.AZURE_SEARCH_SERVICE = "test-search-service"

        try:
            endpoint = settings.azure_search_endpoint
            assert endpoint == "https://test-search-service.search.windows.net"
        finally:
            settings.AZURE_SEARCH_SERVICE = original_service

    def test_azure_openai_endpoint_property(self):
        """Test Azure OpenAI endpoint URL construction"""
        original_service = settings.AZURE_OPENAI_SERVICE
        settings.AZURE_OPENAI_SERVICE = "test-openai-service"

        try:
            endpoint = settings.azure_openai_endpoint
            assert endpoint == "https://test-openai-service.openai.azure.com"
        finally:
            settings.AZURE_OPENAI_SERVICE = original_service

    def test_azure_storage_account_url_property(self):
        """Test Azure storage account URL construction"""
        original_account = settings.AZURE_STORAGE_ACCOUNT
        settings.AZURE_STORAGE_ACCOUNT = "test-storage-account"

        try:
            url = settings.azure_storage_account_url
            assert url == "https://test-storage-account.blob.core.windows.net"
        finally:
            settings.AZURE_STORAGE_ACCOUNT = original_account

    def test_empty_service_names_return_empty_urls(self):
        """Test that empty service names return empty URLs"""
        original_search = settings.AZURE_SEARCH_SERVICE
        original_openai = settings.AZURE_OPENAI_SERVICE
        original_storage = settings.AZURE_STORAGE_ACCOUNT

        settings.AZURE_SEARCH_SERVICE = ""
        settings.AZURE_OPENAI_SERVICE = ""
        settings.AZURE_STORAGE_ACCOUNT = ""

        try:
            assert settings.azure_search_endpoint == ""
            assert settings.azure_openai_endpoint == ""
            assert settings.azure_storage_account_url == ""
        finally:
            settings.AZURE_SEARCH_SERVICE = original_search
            settings.AZURE_OPENAI_SERVICE = original_openai
            settings.AZURE_STORAGE_ACCOUNT = original_storage


class TestIntegrationFlow:
    """Test complete integration flow"""

    @pytest.fixture(autouse=True)
    def clear_config(self):
        """Clear global config before each test"""
        global current_app_config
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        # Clear cache for dependency injection functions
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()
        yield
        current_app_config.clear()
        _approach_registry._preconfigured_instances.clear()
        get_search_client.cache_clear()
        get_openai_client.cache_clear()
        get_blob_client.cache_clear()
        get_auth_helper.cache_clear()

    @pytest.mark.asyncio
    async def test_complete_setup_flow(self):
        """Test the complete setup flow end-to-end"""
        # Start with empty config
        assert len(current_app_config) == 0
        assert not _approach_registry.has_preconfigured_instances()

        # Run setup
        await setup_clients()

        # Verify all clients are configured
        assert get_search_client() is not None
        assert get_openai_client() is not None
        assert get_blob_client() is not None

        # Verify approaches are configured with clients
        from app.approaches import get_approach

        approach = get_approach("retrieve_then_read")
        assert approach.search_client is not None
        assert approach.openai_client is not None

        # Verify configuration is accessible
        assert get_app_config("search_client") is not None
        assert get_app_config("openai_client") is not None

        # Test cleanup
        await cleanup_clients()

    @pytest.mark.asyncio
    async def test_approach_execution_with_setup_clients(self):
        """Test that approaches work correctly with setup clients"""
        await setup_clients()

        from app.approaches import get_approach

        # Get approach with injected clients
        approach = get_approach("retrieve_then_read")

        # Test that approach can be executed
        messages = [{"role": "user", "content": "What is artificial intelligence?"}]

        response = await approach.run(messages=messages, stream=False)

        # Verify response structure
        assert "content" in response
        assert "sources" in response
        assert "context" in response
        assert response["content"] is not None
        assert isinstance(response["sources"], list)
        assert isinstance(response["context"], dict)
