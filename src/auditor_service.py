import requests
from models import RecordingModel


class AuditorService:
    def __init__(self):
        pass

    def process(self, recording: RecordingModel):
        
        r = requests.Session()
        
        data = {
            "file_url": recording.recording_url,
            "company_name": recording.sale_company,
            "average_settle_percentage": recording.weight_percentage,
            "estimated_pay_off_amount": recording.estimated_pay_off_amount,
            "client_first_name": recording.first_name,
            "client_last_name": recording.last_name
        }

        response = r.post(
            url= "https://n8n.srv1027347.hstgr.cloud/webhook/sales-order-audit",
            json=data
        )

        return response
