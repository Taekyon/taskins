from dataclasses import dataclass

import paramiko

# Timeout de connexion uniquement — aucun timeout par commande en V2
# ("timeout par tâche" est explicitement hors périmètre V1, 08-format-yaml.md).
DEFAULT_CONNECT_TIMEOUT = 10


@dataclass
class SSHExecutionResult:
    return_code: int
    stdout: str
    stderr: str


class SSHInfrastructureError(Exception):
    """Échec d'infrastructure (connexion, authentification, timeout, coupure
    pendant l'exécution) — distinct d'un code de retour non nul de la commande
    elle-même. Voir 04-protocole-ssh.md, section 'Distinction importante'."""


def execute_command(
    host: str,
    port: int,
    username: str,
    key_path: str,
    command: str,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> SSHExecutionResult:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            key_filename=key_path,
            timeout=connect_timeout,
        )
    except Exception as e:
        raise SSHInfrastructureError(
            f"Connexion SSH impossible vers {username}@{host}:{port} : {e}"
        ) from e

    try:
        _stdin, stdout, stderr = client.exec_command(command)
        return_code = stdout.channel.recv_exit_status()  # attend la fin complète
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return SSHExecutionResult(return_code=return_code, stdout=out, stderr=err)
    except SSHInfrastructureError:
        raise
    except Exception as e:
        raise SSHInfrastructureError(
            f"Échec pendant l'exécution de la commande sur {host} : {e}"
        ) from e
    finally:
        client.close()  # fermeture immédiate — 04-protocole-ssh.md, étape 6
