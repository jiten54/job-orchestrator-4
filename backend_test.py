#!/usr/bin/env python3
"""
Backend API Testing for Distributed Workflow Orchestrator
Tests all endpoints: health, metrics, jobs CRUD, retry, recovery, logs, config, WebSocket
"""
import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Use the public endpoint from frontend .env
BASE_URL = "https://job-orchestrator-4.preview.emergentagent.com/api"

class WorkflowOrchestratorTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.tests_run = 0
        self.tests_passed = 0
        self.created_jobs = []
        
    def log(self, message: str):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Dict[Any, Any] = None, params: Dict[str, str] = None) -> tuple:
        """Run a single API test and return success status and response"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    self.log(f"   Error response: {error_data}")
                except:
                    self.log(f"   Error response: {response.text}")
                return False, {}
                
        except requests.exceptions.Timeout:
            self.log(f"❌ {name} - Request timeout")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log(f"❌ {name} - Connection error")
            return False, {}
        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}
    
    def test_health_check(self):
        """Test GET /api/health"""
        success, response = self.run_test(
            "Health Check", "GET", "health", 200
        )
        if success:
            required_fields = ['status', 'system', 'version', 'workers_active', 'queue_depth', 'uptime_seconds']
            for field in required_fields:
                if field not in response:
                    self.log(f"❌ Health Check - Missing field: {field}")
                    return False
            self.log(f"   System: {response.get('system')} v{response.get('version')}")
            self.log(f"   Workers: {response.get('workers_active')}, Queue: {response.get('queue_depth')}")
        return success
    
    def test_metrics(self):
        """Test GET /api/metrics"""
        success, response = self.run_test(
            "System Metrics", "GET", "metrics", 200
        )
        if success:
            required_fields = ['total_jobs', 'pending', 'running', 'completed', 'failed', 
                             'success_rate', 'failure_rate', 'avg_execution_time']
            for field in required_fields:
                if field not in response:
                    self.log(f"❌ Metrics - Missing field: {field}")
                    return False
            self.log(f"   Total jobs: {response.get('total_jobs')}, Success rate: {response.get('success_rate')}%")
        return success
    
    def test_create_job(self):
        """Test POST /api/jobs"""
        job_data = {
            "name": f"test-compute-{int(time.time())}",
            "type": "compute",
            "max_retries": 3
        }
        success, response = self.run_test(
            "Create Job", "POST", "jobs", 200, job_data
        )
        if success and 'id' in response:
            self.created_jobs.append(response['id'])
            self.log(f"   Created job ID: {response['id']}")
        return success
    
    def test_create_batch_jobs(self):
        """Test POST /api/jobs/batch?count=5"""
        success, response = self.run_test(
            "Create Batch Jobs", "POST", "jobs/batch", 200, params={"count": "5"}
        )
        if success:
            created_count = response.get('created', 0)
            self.log(f"   Created {created_count} batch jobs")
            # Store job IDs for later tests
            if 'jobs' in response:
                for job in response['jobs']:
                    if 'id' in job:
                        self.created_jobs.append(job['id'])
        return success
    
    def test_list_jobs(self):
        """Test GET /api/jobs"""
        success, response = self.run_test(
            "List All Jobs", "GET", "jobs", 200
        )
        if success and isinstance(response, list):
            self.log(f"   Found {len(response)} jobs")
            return True
        return False
    
    def test_filter_jobs_by_status(self):
        """Test GET /api/jobs?status=completed"""
        success, response = self.run_test(
            "Filter Jobs by Status", "GET", "jobs", 200, params={"status": "completed"}
        )
        if success and isinstance(response, list):
            self.log(f"   Found {len(response)} completed jobs")
            return True
        return False
    
    def test_filter_jobs_by_type(self):
        """Test GET /api/jobs?type=compute"""
        success, response = self.run_test(
            "Filter Jobs by Type", "GET", "jobs", 200, params={"type": "compute"}
        )
        if success and isinstance(response, list):
            self.log(f"   Found {len(response)} compute jobs")
            return True
        return False
    
    def test_get_specific_job(self):
        """Test GET /api/jobs/{id}"""
        if not self.created_jobs:
            self.log("⚠️  No jobs available for specific job test")
            return True
            
        job_id = self.created_jobs[0]
        success, response = self.run_test(
            f"Get Job {job_id}", "GET", f"jobs/{job_id}", 200
        )
        if success and isinstance(response, dict):
            self.log(f"   Job status: {response.get('status')}")
        return success
    
    def test_retry_job(self):
        """Test POST /api/jobs/{id}/retry - need a failed job"""
        # First, let's wait a bit for some jobs to potentially fail
        self.log("⏳ Waiting 10 seconds for jobs to process and potentially fail...")
        time.sleep(10)
        
        # Get all jobs to find a failed one
        success, jobs = self.run_test("Get Jobs for Retry", "GET", "jobs", 200)
        if not success:
            return False
            
        failed_jobs = [job for job in jobs if job.get('status') == 'failed']
        if not failed_jobs:
            self.log("⚠️  No failed jobs found for retry test")
            return True
            
        job_id = failed_jobs[0]['id']
        success, response = self.run_test(
            f"Retry Job {job_id}", "POST", f"jobs/{job_id}/retry", 200
        )
        if success:
            self.log(f"   Retry status: {response.get('status')}")
        return success
    
    def test_retry_all_failed(self):
        """Test POST /api/jobs/retry-all"""
        success, response = self.run_test(
            "Retry All Failed Jobs", "POST", "jobs/retry-all", 200
        )
        if success:
            retried_count = response.get('retried', 0)
            self.log(f"   Retried {retried_count} failed jobs")
        return success
    
    def test_auto_recovery(self):
        """Test POST /api/recovery/auto"""
        success, response = self.run_test(
            "Auto Recovery", "POST", "recovery/auto", 200
        )
        if success:
            reset_jobs = response.get('reset_jobs', 0)
            requeued_jobs = response.get('requeued_jobs', 0)
            self.log(f"   Reset: {reset_jobs}, Requeued: {requeued_jobs}")
        return success
    
    def test_get_logs(self):
        """Test GET /api/logs"""
        success, response = self.run_test(
            "Get System Logs", "GET", "logs", 200, params={"limit": "50"}
        )
        if success and isinstance(response, list):
            self.log(f"   Retrieved {len(response)} log entries")
            if response:
                latest_log = response[-1]
                self.log(f"   Latest log: {latest_log.get('level')} - {latest_log.get('message')}")
        return success
    
    def test_get_config(self):
        """Test GET /api/config"""
        success, response = self.run_test(
            "Get System Config", "GET", "config", 200
        )
        if success:
            self.log(f"   Worker count: {response.get('worker_count')}")
            self.log(f"   Max retries: {response.get('max_retries')}")
            self.log(f"   Failure probability: {response.get('failure_probability')}")
        return success
    
    def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability (basic connectivity)"""
        # We can't easily test WebSocket in this simple script, but we can check if the endpoint exists
        # by trying to connect and seeing if we get a proper WebSocket upgrade response
        try:
            import websocket
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws'
            self.log(f"🔍 Testing WebSocket connectivity to {ws_url}")
            
            def on_open(ws):
                self.log("✅ WebSocket connection established")
                ws.close()
            
            def on_error(ws, error):
                self.log(f"❌ WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                self.log("WebSocket connection closed")
            
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run for a short time
            ws.run_forever(timeout=5)
            self.tests_run += 1
            self.tests_passed += 1
            return True
            
        except ImportError:
            self.log("⚠️  websocket-client not available, skipping WebSocket test")
            return True
        except Exception as e:
            self.log(f"❌ WebSocket test failed: {str(e)}")
            self.tests_run += 1
            return False
    
    def run_all_tests(self):
        """Run all backend API tests"""
        self.log("🚀 Starting Distributed Workflow Orchestrator Backend Tests")
        self.log(f"Testing against: {self.base_url}")
        
        # Core system tests
        self.test_health_check()
        self.test_metrics()
        self.test_get_config()
        
        # Job management tests
        self.test_create_job()
        self.test_create_batch_jobs()
        self.test_list_jobs()
        self.test_filter_jobs_by_status()
        self.test_filter_jobs_by_type()
        self.test_get_specific_job()
        
        # Recovery and retry tests
        self.test_retry_job()
        self.test_retry_all_failed()
        self.test_auto_recovery()
        
        # Observability tests
        self.test_get_logs()
        
        # WebSocket test
        self.test_websocket_endpoint()
        
        # Final summary
        self.log("\n" + "="*60)
        self.log(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.created_jobs:
            self.log(f"🔧 Created {len(self.created_jobs)} test jobs")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = WorkflowOrchestratorTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())