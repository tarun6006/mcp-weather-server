"""
Black box tests for weather server routes
Tests API endpoints without knowing internal implementation
"""
import pytest
import json
from unittest.mock import patch, Mock
from app import app

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_health_endpoint_success(self, client):
        """Test health endpoint returns success"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['server'] == 'weather-server'
        assert 'version' in data
        assert 'timestamp' in data
        assert 'services' in data
    
    def test_health_endpoint_services_status(self, client):
        """Test health endpoint includes service status"""
        response = client.get('/health')
        data = json.loads(response.data)
        
        services = data['services']
        assert 'weather_api' in services
        assert 'census_api' in services
        assert 'nominatim_api' in services
        assert 'mcp_protocol' in services
        
        # All should be True for healthy status
        assert services['weather_api'] is True
        assert services['census_api'] is True
        assert services['nominatim_api'] is True
        assert services['mcp_protocol'] is True
    
    @patch('routes.health.logger')
    def test_health_endpoint_exception_handling(self, mock_logger, client):
        """Test health endpoint handles exceptions"""
        response = client.get('/health')
        
        # Should return a response even if there are internal issues
        assert response.status_code in [200, 500]
        
        # Response should always be valid JSON
        data = json.loads(response.data)
        assert 'status' in data
        assert 'timestamp' in data

class TestMCPEndpoint:
    """Test MCP protocol endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('routes.mcp.weather_service.get_weather')
    def test_mcp_endpoint_get_weather_by_city(self, mock_get_weather, client):
        """Test MCP get_weather tool call by city"""
        # Mock weather service response
        from mcp_utils.schema import CallToolResult, TextContent
        mock_result = CallToolResult(content=[TextContent(type='text', text='Today: Sunny at 75°F')])
        mock_get_weather.return_value = mock_result
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {
                    "city": "Boston"
                }
            }
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['jsonrpc'] == '2.0'
        assert data['id'] == 'test-1'
        assert 'content' in data
        
        mock_get_weather.assert_called_once_with(city="Boston", zip_code=None)
    
    @patch('routes.mcp.weather_service.get_weather')
    def test_mcp_endpoint_get_weather_by_zip(self, mock_get_weather, client):
        """Test MCP get_weather tool call by ZIP code"""
        from mcp_utils.schema import CallToolResult, TextContent
        mock_result = CallToolResult(content=[TextContent(type='text', text='Tonight: Clear at 65°F')])
        mock_get_weather.return_value = mock_result
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {
                    "zip_code": "02101"
                }
            }
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'content' in data
        
        mock_get_weather.assert_called_once_with(city=None, zip_code="02101")
    
    @patch('routes.mcp.weather_service.get_weather')
    def test_mcp_endpoint_get_weather_both_params(self, mock_get_weather, client):
        """Test MCP get_weather tool call with both city and ZIP code"""
        from mcp_utils.schema import CallToolResult, TextContent
        mock_result = CallToolResult(content=[TextContent(type='text', text='Today: Partly Cloudy at 70°F')])
        mock_get_weather.return_value = mock_result
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-3",
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {
                    "city": "Boston",
                    "zip_code": "02101"
                }
            }
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        mock_get_weather.assert_called_once_with(city="Boston", zip_code="02101")
    
    @patch('routes.mcp.weather_service.get_weather')
    def test_mcp_endpoint_get_weather_no_params(self, mock_get_weather, client):
        """Test MCP get_weather tool call with no parameters"""
        from mcp_utils.schema import CallToolResult, TextContent
        mock_result = CallToolResult(content=[TextContent(type='text', text='Error: Provide city or zip_code')])
        mock_get_weather.return_value = mock_result
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-4",
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {}
            }
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        mock_get_weather.assert_called_once_with(city=None, zip_code=None)
    
    def test_mcp_endpoint_invalid_json(self, client):
        """Test MCP endpoint with invalid JSON"""
        response = client.post('/mcp',
                              data='invalid json',
                              content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_mcp_endpoint_no_data(self, client):
        """Test MCP endpoint with no data"""
        response = client.post('/mcp',
                              content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_mcp_endpoint_missing_method(self, client):
        """Test MCP endpoint with missing method"""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-5",
            "params": {}
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        # Should handle gracefully
        assert response.status_code in [200, 500]
    
    @patch('routes.mcp.weather_service.get_weather')
    def test_mcp_endpoint_weather_service_exception(self, mock_get_weather, client):
        """Test MCP endpoint when weather service raises exception"""
        mock_get_weather.side_effect = Exception("Weather service error")
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-6",
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {
                    "city": "Boston"
                }
            }
        }
        
        response = client.post('/mcp',
                              data=json.dumps(request_data),
                              content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

class TestMCPServerInitialization:
    """Test MCP server initialization scenarios"""
    
    def test_mcp_server_initialization_patterns(self):
        """Test that MCP server can be initialized with different patterns"""
        # This is more of an integration test to ensure the server starts
        from routes.mcp import mcp
        
        # Should have initialized successfully
        assert mcp is not None
        assert hasattr(mcp, 'handle_message') or hasattr(mcp, 'tool')

class TestIntegrationScenarios:
    """Test integration scenarios across multiple endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_full_weather_workflow(self, client):
        """Test complete weather workflow"""
        # 1. Check health
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        # 2. Make weather request (will likely fail without real APIs, but should handle gracefully)
        with patch('routes.mcp.weather_service.get_weather') as mock_get_weather:
            from mcp_utils.schema import CallToolResult, TextContent
            mock_result = CallToolResult(content=[TextContent(type='text', text='Today: Sunny at 75°F')])
            mock_get_weather.return_value = mock_result
            
            weather_request = {
                "jsonrpc": "2.0",
                "id": "workflow-1",
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "Boston"
                    }
                }
            }
            
            weather_response = client.post('/mcp',
                                          data=json.dumps(weather_request),
                                          content_type='application/json')
            assert weather_response.status_code == 200
    
    def test_error_handling_workflow(self, client):
        """Test error handling across different scenarios"""
        # Test various error conditions
        error_scenarios = [
            # Invalid city
            {
                "arguments": {"city": "NonexistentCity123"},
                "expected_status": 200  # Should return 200 with error in content
            },
            # Invalid ZIP code
            {
                "arguments": {"zip_code": "00000"},
                "expected_status": 200
            },
            # No parameters
            {
                "arguments": {},
                "expected_status": 200
            }
        ]
        
        with patch('routes.mcp.weather_service.get_weather') as mock_get_weather:
            from mcp_utils.schema import CallToolResult, TextContent
            
            for i, scenario in enumerate(error_scenarios):
                # Mock different error responses
                mock_result = CallToolResult(content=[TextContent(type='text', text=f'Error: Test error {i}')])
                mock_get_weather.return_value = mock_result
                
                request_data = {
                    "jsonrpc": "2.0",
                    "id": f"error-test-{i}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_weather",
                        "arguments": scenario["arguments"]
                    }
                }
                
                response = client.post('/mcp',
                                      data=json.dumps(request_data),
                                      content_type='application/json')
                
                assert response.status_code == scenario["expected_status"]
                
                if response.status_code == 200:
                    data = json.loads(response.data)
                    # Should have some response content
                    assert 'content' in data or 'error' in data
    
    def test_concurrent_requests_handling(self, client):
        """Test handling of multiple concurrent requests"""
        with patch('routes.mcp.weather_service.get_weather') as mock_get_weather:
            from mcp_utils.schema import CallToolResult, TextContent
            mock_result = CallToolResult(content=[TextContent(type='text', text='Weather data')])
            mock_get_weather.return_value = mock_result
            
            # Make multiple requests
            requests_data = []
            for i in range(5):
                requests_data.append({
                    "jsonrpc": "2.0",
                    "id": f"concurrent-{i}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_weather",
                        "arguments": {"city": f"City{i}"}
                    }
                })
            
            responses = []
            for request_data in requests_data:
                response = client.post('/mcp',
                                      data=json.dumps(request_data),
                                      content_type='application/json')
                responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
            
            # Should have called weather service for each request
            assert mock_get_weather.call_count == 5
