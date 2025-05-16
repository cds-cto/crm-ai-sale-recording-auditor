from service import AISaleService
import debugpy
from datetime import datetime, timedelta
import pytz


def main():
    utc_now = datetime.now(pytz.utc)
    pdt_timezone = pytz.timezone("America/Los_Angeles")
    pdt_now = utc_now.astimezone(pdt_timezone)

    ai_sale_service = AISaleService()
    # for testing
    # ai_sale_service.process_check_gpt()
    ai_sale_service.process(
        from_date_time=pdt_now,
        to_date_time=pdt_now + timedelta(days=1),
    )

    utc_now_end = datetime.now(pytz.utc)
    pdt_now_end = utc_now_end.astimezone(pdt_timezone)

    print(f"Process started at    = {pdt_now}")
    print(f"Process completed at   = {pdt_now_end}")


# main
if __name__ == "__main__":
    # debugpy.listen(("0.0.0.0", 5678))
    # debugpy.wait_for_client()
    # breakpoint()
    main()
