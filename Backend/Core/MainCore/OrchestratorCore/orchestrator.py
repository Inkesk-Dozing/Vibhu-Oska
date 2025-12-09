#Importing From MainCore packages and SpecializedCore packages and BackupCore packages 
#so they can be utilized in the orchestrator module to give respective functionalities.

from Backend.Core.SpecializedCore import DataCore
from Core.BackupCore.backup1 import BackupCore1
from Backend.Core.MainCore.CognitionCore.cognition import Cognition
from Backend.Core.MainCore.MonitoringCore.monitoring import Monitoring
from Backend.Core.MainCore.OptimizationCore.optimization import Optimization
from Backend.Core.MainCore.ValidationCore.validation import Validation
# from a folder - sub folder - sub sub folder - sub sub sub folder - python files importing class
 

class Orchestrator:
    def __init__(self):
        self.monitoring    =  Monitoring()
        self.optimization  =  Optimization()
        self.validation    =  Validation()
        self.cognition     =  Cognition()
        # self.text_summarization = TextSummarizationCore.TextSummarizationCore()
        # self.sentiment_analysis = SentimentAnalysisCore.SentimentAnalysisCore()
        # self.text_classification = TextClassificationCore.TextClassificationCore()
        self.backup1 = BackupCore1()
        
    def process_request(self, request):
        """
        Orchestrates the processing of a request through -
        validation, cognition, optimization, and monitoring.
        """
        # 1. Start Watch
        start_t = self.monitoring.start_timer()

        # ... do work (Cognition, etc.) ...
        
        # 2. Log success (Monitoring Core auto-checks for latency alerts)
        self.monitoring.log_event("Orchestrator: Request processed successfully", start_t)
        
    def process_request1(self, request_data):
        """
        Orchestrates the processing of a request through the core pipeline.
        """
        start_time = self.monitoring.start_timer()
        response = None

        try:
            # 1. VALIDATION CORE (Check safety and format)
            if not self.validation.validate_request(request_data):
                self.monitoring.log_event("Orchestrator : Validation Failed: Invalid Data", start_time)
                return {"status": "error", "message": "Input failed validation."}

            # 2. COGNITION CORE (The core processing logic)
            raw_result = self.cognition.process(request_data)

            # 3. OPTIMIZATION CORE (Refining the output)
            final_result = self.optimization.optimize(raw_result)
                    
                    # --- MONITORING CHECKPOINT ---
                    # 4. Use the imported function 'evaluate' directly for a quick pass/fail
            if not Monitoring.evaluate(final_result,reflections=""):
                msg="Optimization Check Failed!"
                self.monitoring.send_alert(msg)
                raise ValueError("Optimization output failed final quality check.")

            # 5. BACKUP CORE (Saving state before final return)
            self.backup1.save(final_result)

            # 6. LOG SUCCESS & RETURN
            self.monitoring.log_event("Orchestrator : Request processed successfully", start_time)
            return {"status": "success", "data": final_result}

        except Exception as e:
            # Central failure logging using the monitoring object
            self.monitoring.log_event(f"Orchestrator : CRITICAL ERROR: {e}", start_time)
            return {"status": "fatal_error", "message": "Orchestration terminated due to internal failure."}