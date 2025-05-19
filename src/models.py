from pydantic import BaseModel
from typing import List


class SettlementPaymentModel(BaseModel):
    SettlementPaymentId: str
    ProfileName: str
    LiabilityId: str
    # LiabilityName: str
    # OriginalCreditorId: str
    # OriginalCreditorName: str
    CurrentCreditorId: str
    CurrentCreditorName: str
    # SettlementOfferId: str
    PaymentStatus: int
    # PaymentStatusName: str
    SettlementPaymentCategory: int
    # SettlementPaymentCategoryName: str
    OfferReferenceId: str
    Locked: bool
    SettlementPaymentMethod: str = None


class SettlementPaymentBatchModel(BaseModel):
    batch: List[SettlementPaymentModel]


class RecordingModel(BaseModel):
    document_name: str
    document_id: str
    document_title: str
    profile_id: str
    first_name: str
    last_name: str
    sale_company: str
    sale_employee_id: str
    sale_employee_name: str
    document_uploaded_by_id: str
    document_uploaded_by_name: str
    document_uploaded_at: str
    success: bool
    duration: int
    transcript: str = None
    error_code_list: List[dict] = None
    # ********  extra fields
    recording_url: str
    recording_file_path: str
    weight_percentage: str = None
    file_extension: str = None
    profile_status: str = None
    enrolled_date: str = None


class RecordingBatchModel(BaseModel):
    batch: List[RecordingModel]


class WeightPercentageModel(BaseModel):
    enrolled: bool
    accountType: int
    averageSettlementLegalPercentage: float
    averageSettlementPercentage: float
    originalBalance: float
