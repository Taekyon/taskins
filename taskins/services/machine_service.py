from sqlalchemy.orm import Session

from taskins.models.machine import Machine
from taskins.schemas.machine import MachineCreate


def list_machines(db: Session) -> list[Machine]:
    return db.query(Machine).order_by(Machine.alias).all()


def get_machine_by_alias(db: Session, alias: str) -> Machine | None:
    return db.query(Machine).filter_by(alias=alias).first()


def create_machine(db: Session, data: MachineCreate) -> Machine:
    machine = Machine(
        alias=data.alias,
        host=data.host,
        ssh_user=data.ssh_user,
        ssh_port=data.ssh_port,
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


class MachineValidationError(Exception):
    pass


def get_machine(db: Session, machine_id: int) -> Machine | None:
    return db.get(Machine, machine_id)


def delete_machine(db: Session, machine: Machine) -> None:
    """Refuse la suppression si la machine est encore référencée : supprimer une
    machine utilisée par une tâche casserait la définition d'un workflow validé,
    ce qui contredirait l'exigence d'immuabilité."""
    from taskins.models.execution import Execution
    from taskins.models.task import Task

    n_tasks = db.query(Task).filter_by(machine_id=machine.id).count()
    n_execs = db.query(Execution).filter_by(machine_id=machine.id).count()

    if n_tasks or n_execs:
        details = []
        if n_tasks:
            details.append(f"{n_tasks} tâche(s)")
        if n_execs:
            details.append(f"{n_execs} exécution(s) redirigée(s)")
        raise MachineValidationError(
            f"Machine '{machine.alias}' encore référencée par {' et '.join(details)}. "
            "Supprimer ou archiver les workflows concernés d'abord."
        )

    db.delete(machine)
    db.commit()
