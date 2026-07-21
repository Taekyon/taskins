import time
from dataclasses import dataclass

import paramiko

DEFAULT_CONNECT_TIMEOUT = 10
POLL_INTERVAL = 0.2       # fréquence de scrutation de la fin de commande
READ_CHUNK = 65536


@dataclass
class SSHExecutionResult:
    return_code: int
    stdout: str
    stderr: str


class SSHInfrastructureError(Exception):
    """Échec d'infrastructure (connexion, authentification, coupure) — distinct
    d'un code de retour non nul de la commande. Voir 04-protocole-ssh.md."""


class SSHTimeoutError(SSHInfrastructureError):
    """La commande n'a pas rendu la main dans le délai imparti. Sous-classe de
    SSHInfrastructureError : le moteur la traite comme un échec (task_result
    FAILED), conformément à la décision prise en V1."""


def execute_command(
    host: str,
    port: int,
    username: str,
    key_path: str,
    command: str,
    timeout_seconds: int,
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
        client.close()
        raise SSHInfrastructureError(
            f"Connexion SSH impossible vers {username}@{host}:{port} : {e}"
        ) from e

    channel = None
    try:
        channel = client.get_transport().open_session()
        channel.settimeout(POLL_INTERVAL)
        channel.exec_command(command)

        out_chunks: list[bytes] = []
        err_chunks: list[bytes] = []
        deadline = time.monotonic() + timeout_seconds

        while True:
            # Vider les tampons à chaque tour : sans ça, une commande verbeuse
            # sature le buffer du canal, le processus distant bloque en écriture
            # et la commande ne se termine jamais (interblocage).
            while channel.recv_ready():
                out_chunks.append(channel.recv(READ_CHUNK))
            while channel.recv_stderr_ready():
                err_chunks.append(channel.recv_stderr(READ_CHUNK))

            if channel.exit_status_ready():
                break

            if time.monotonic() > deadline:
                raise SSHTimeoutError(
                    f"Timeout : la commande n'a pas rendu la main en {timeout_seconds}s "
                    f"sur {username}@{host}:{port}"
                )

            time.sleep(POLL_INTERVAL)

        # Purge finale de ce qui reste après la sortie du processus.
        while channel.recv_ready():
            out_chunks.append(channel.recv(READ_CHUNK))
        while channel.recv_stderr_ready():
            err_chunks.append(channel.recv_stderr(READ_CHUNK))

        return SSHExecutionResult(
            return_code=channel.recv_exit_status(),
            stdout=b"".join(out_chunks).decode(errors="replace"),
            stderr=b"".join(err_chunks).decode(errors="replace"),
        )
    except SSHInfrastructureError:
        raise
    except Exception as e:
        raise SSHInfrastructureError(
            f"Échec pendant l'exécution de la commande sur {host} : {e}"
        ) from e
    finally:
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass
        client.close()  # fermeture immédiate — 04-protocole-ssh.md, étape 6
