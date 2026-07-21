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
