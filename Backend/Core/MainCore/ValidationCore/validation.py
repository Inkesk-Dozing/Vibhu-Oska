
class Validation:
    
    def __init__(self):
        pass

    # ==================================================================================================
    # 1. PUBLIC API (This is what OrchestratorCore calls)
    # ==================================================================================================

    def validate_request(self,raw_data):
        '''
        Docstring for validate_request
        '''
        pass
        
    def validate_input_package(self, raw_data):
        """
        The 'Entry Gate'. Checks Security + Basic Schema.
        Returns: (bool, reason)
        """
        # Step A: Security (The "Police")
        if not self._check_security(raw_data):
            return False, "Security Risk Detected"

        # Step B: Format (The "Clerk")
        if not self._check_format(raw_data):
            return False, "Invalid Data Format"
            
        return True, "Valid"
    
    def validate_ai_output(self, ai_response):
        """
        The 'Exit Gate'. Checks if AI response is safe/valid.
        """
        # Step A: Completeness
        if not self._check_completeness(ai_response):
            return False, "AI response incomplete"
            
        # Step B: Protocol (Ensure it matches brain.proto)
        if not self._verify_protocol(ai_response):
            return False, "Protocol Mismatch"

        return True, "Valid"

    # ==================================================================================================
    # 2. INTERNAL LOGIC (The actual workers)
    #    (Note: These are private methods, denoted by _ as access modifiers)
    # ==================================================================================================

    def _check_security(self, data):
        """authenticate, audit, confirm_integrity"""
        # check for SQL injection patterns
        if "DROP TABLE" in str(data) or "<script>" in str(data):
            return False
        return True

    def _check_format(self, data):
        """validate_format, check_consistency"""
        # Check if it is a dictionary or valid JSON
        if not isinstance(data, (dict, str)):
            return False
        return True

    def _check_completeness(self, data):
        """ validate_completeness, validate_accuracy"""
        # Did the AI return empty text?
        if not data or len(str(data)) < 1:
            return False
        return True
        
    def _verify_protocol(self, data):
        """verify, certify, review"""
        # Does it have the required fields?
        required_fields = ["text_response", "action_code"]
        for field in required_fields:
            if field not in data.__dict__: # Assuming data is an object
                return False
        return True
    