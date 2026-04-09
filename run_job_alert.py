from job_alert.runner import JobAlertRunner


def main() -> None:
    runner = JobAlertRunner()
    summary = runner.run_all()
    print(summary.render_text())


if __name__ == "__main__":
    main()
