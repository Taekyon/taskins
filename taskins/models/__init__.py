# Importer tous les modèles ici pour les enregistrer auprès de Base.metadata
# avant tout appel à Base.metadata.create_all().
from taskins.models.user_group import user_groups  # noqa: F401 — table de liaison, doit être en premier
from taskins.models.user import User  # noqa: F401
from taskins.models.group import Group  # noqa: F401
from taskins.models.machine import Machine  # noqa: F401
from taskins.models.workflow import Workflow  # noqa: F401
from taskins.models.task import Task  # noqa: F401
from taskins.models.execution import Execution  # noqa: F401
from taskins.models.task_result import TaskResult  # noqa: F401