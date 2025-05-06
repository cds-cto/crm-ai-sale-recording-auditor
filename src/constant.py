class TRANSACTION_CODES:
    # General
    class GENERAL:
        class ERROR_CODE:
            E100 = "Claims that program is from the government"
            E101 = "Claims that we are a loan company or will loan money to clients"
            E102 = "Claims that we do debt validation"
            E103 = "Claims that we do credit repair"
            E104 = "Claims that we will have an attorney represent clients if anything happens"
            E105 = "Claims that we do not charge any fees"
            E106 = "Claims that we can achieve better settlement percentage than the quoted amount"
            E107 = "Claims that we will refund if clients are not happy"
            E108 = "Claims that the client can cancel anytime without any issue"
            E109 = "Claims that credit score won't have any impact or only short-term impact"
            E110 = "Claims that enrolled accounts will be temporarily closed after or during the settlement"
            E111 = "Claims that program will not affect client's military/security clearance"
            E112 = "Claims that client can keep using the same bank who issued the enrolled credit cards"
            E113 = "Claims that the client won't get sued"
            E114 = "Claims or accepts an account with promotional interest or zero interest for enrollment"
            E115 = "Claims or accepts secured debt to the program"
            E116 = "Claims that the program does not require the client's active engagement and responsiveness"
            E117 = "Failure to disclose that the client owns and controls the dedicated account"
            E118 = "Claims that we have full control over client's dedicated account"

            S115 = "Salesperson did not go through budgeting with client"

            F100 = "Base on the content, the recording wasn't a sales recording"
            F101 = "Base on the extension type, the file is not an audio file"

            #######
            X100 = "Document already exists in mongo"

        class STANDARD_CODE:
            SUCCESS = "SUCCESS"

    @staticmethod
    def is_error_code_used(code):
        """Recursively check if the given code exists in any ERROR_CODE class."""

        def check_class(cls):
            """Recursively check all nested ERROR_CODE classes."""
            for attr_name, attr_value in vars(cls).items():
                if isinstance(attr_value, type):  # If it's a nested class
                    if attr_name == "ERROR_CODE":  # Only check ERROR_CODE classes
                        if code in vars(attr_value).values():
                            return True
                    elif check_class(attr_value):  # Recursively check other classes
                        return True
            return False

        return check_class(TRANSACTION_CODES)
