from sqlalchemy.orm import Session

from taskins.models.group import Group

# Groupe structurant créé par le seed : toute création de workflow s'y rattache
# en V1 (voir workflow_service._default_group). Sa suppression casserait l'app.
PROTECTED_GROUP = "all"


class GroupValidationError(Exception):
    pass


def list_groups(db: Session) -> list[Group]:
    return db.query(Group).order_by(Group.name).all()


def get_group(db: Session, group_id: int) -> Group | None:
    return db.get(Group, group_id)


def create_group(db: Session, name: str) -> Group:
    group = Group(name=name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group: Group) -> None:
    from taskins.models.workflow import Workflow

    if group.name == PROTECTED_GROUP:
        raise GroupValidationError(
            f"Le groupe '{PROTECTED_GROUP}' est structurant et ne peut pas être supprimé"
        )

    n_workflows = db.query(Workflow).filter_by(group_id=group.id).count()
    if n_workflows:
        raise GroupValidationError(
            f"Le groupe '{group.name}' contient encore {n_workflows} workflow(s)."
        )

    db.delete(group)  # user_groups part en cascade (ON DELETE CASCADE)
    db.commit()
