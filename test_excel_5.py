from datetime import date, timedelta
from pathlib import Path

from meapp.config.settings import Settings
from meapp.zoho.authenticator import ZohoAuthenticator
from meapp.zoho.mail_client import ZohoMailClient

from meapp.parsers.maintenance import maintenance_parser
from meapp.excel.writer import ExcelManager


def is_maintenance_mail(mail_subject: str) -> bool:
    # MAINTENANCE REPORT
    try:
        if mail_subject.lower().startswith("re:"):
            return False
        return mail_subject.strip().lower().startswith("maintenance report")
    
    except ValueError:
        return False



def main() -> None:
    print("=" * 60)
    print("MEApp Phase 4Test")
    print("=" * 60)


    settings = Settings()

    authenticator = ZohoAuthenticator(settings)

    access_token = authenticator.get_access_token()

    if not access_token:
        raise RuntimeError("No access token was returned.")

    cached_token = authenticator.get_access_token()

    if cached_token != access_token:
        raise RuntimeError(
            "Cached access token does not match the original token."
        )

    mail_client = ZohoMailClient(authenticator)

    account_id = mail_client.get_account_id()

    if not account_id:
        raise RuntimeError("No Zoho Mail account ID was returned.")



    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 7) #22


    processing_date = start_date
    maintenance_wb_path = Path(r"C:\Users\user\Documents\Internship\SAM-ACE\DATA EXTRACTION\MAINTENANCE REPORT\MEApp\resources\maintenance report.xlsx")

    with ExcelManager(maintenance_wb_path) as excel_application:
        excel_application.open_worksheet("MAINTENANCE DATA")

        processing_date = start_date
        while processing_date <= end_date:
            print(f"Retrieving messages for {processing_date.isoformat()}...")

            messages = mail_client.get_messages_for_date(
                account_id=account_id,
                processing_date=processing_date,
            )
            print(f"Messages retrieved: {len(messages)}")

            maintenance_mails = [m for m in messages if is_maintenance_mail(m["subject"])]
            print(f"\n[8] Got {len(maintenance_mails)} maintenance mails for {processing_date.isoformat()}")

            for maintenance_mail in maintenance_mails:
                print(maintenance_mail["subject"])
                content = mail_client.get_message_content(
                    account_id, maintenance_mail["folderId"], maintenance_mail["messageId"]
                )

                maintenance_report = maintenance_parser(content, processing_date)
                print(maintenance_report)

                excel_application.write_record(maintenance_report)


        

            processing_date += timedelta(days=1)

        excel_application.save_progress = True

    # ---------------------------------------------------------
    # 10. Complete
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("PHASE 4 TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()