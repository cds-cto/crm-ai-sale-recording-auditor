from service import AISaleService
import debugpy
from datetime import datetime
import pytz


def main():
    utc_now = datetime.now(pytz.utc)
    pdt_timezone = pytz.timezone("America/Los_Angeles")
    pdt_now = utc_now.astimezone(pdt_timezone)

    ai_sale_service = AISaleService()
    ai_sale_service.process()

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
