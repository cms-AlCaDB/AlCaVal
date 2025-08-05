from datetime import datetime, timedelta
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from application.services.relval_update_service import RelvalUpdateService
from application.services.dashboard_service import DashboardService
from application import create_app
from core_lib.utils.global_config import Config


app = create_app()

scheduler = BackgroundScheduler()
relvalUpdateService = RelvalUpdateService()
dashboardService = DashboardService()
scheduler.add_job(
    func=lambda: dashboardService.process_relval_transitions(app),
    trigger="interval",
    minutes=15,
    id="relval_transition_job",
    name="RelVals transition processing",
    next_run_time=datetime.now() + timedelta(seconds=60),
    misfire_grace_time=60,
    max_instances=1,  # prevent duplicate job
)
scheduler.add_job(
    func=lambda: relvalUpdateService.check_workflow_status(app),
    trigger="interval",
    minutes=15,
    id="relval_update_job",
    name="RelVal update job",
    next_run_time=datetime.now() + timedelta(seconds=60),
    misfire_grace_time=60,
    max_instances=1,
)
scheduler.start()
atexit.register(scheduler.shutdown)

if __name__ == "__main__":
    app.run(
        debug=Config.get("development"),
        port=Config.get("port"),
        host=Config.get("host"),
    )
