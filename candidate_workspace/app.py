"""
Active Candidate Microservice Runner:
Defaults to V2 Converged Cloud Run application. Can toggle to V1 Naive for comparative benchmarking.
"""

import os
import sys

# Environment variable to switch candidate version
CANDIDATE_VERSION = os.getenv("CANDIDATE_VERSION", "v2").lower()

if CANDIDATE_VERSION == "v1":
    from candidate_workspace.v1_naive.app import app
else:
    from candidate_workspace.v2_converged.app import app

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
