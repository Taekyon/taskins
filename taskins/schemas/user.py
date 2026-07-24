from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Mise à jour par un administrateur. Les deux champs sont optionnels :
    fournir `password` réinitialise le mot de passe sans connaître l'ancien —
    seul recours possible pour un utilisateur qui a oublié le sien, faute de
    procédure de récupération par email."""

    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class PasswordChange(BaseModel):
    """Changement par l'utilisateur lui-même. L'ancien mot de passe est exigé :
    il empêche qu'une session laissée ouverte suffise à confisquer le compte."""

    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = {"from_attributes": True}
