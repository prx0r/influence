from .appstore import AppStoreConnector
from .artifact import LocalArtifactConnector
from .browser import BrowserConnector
from .domain import DomainConnector, WebsiteConnector
from .github import GitHubConnector
from .inbox import InboxConnector
from .names import NamesConnector
from .phone import PhoneConnector
from .postiz import PostizConnector
from .publisher import PublisherConnector
from .registrar import RegistrarConnector
from .social import SocialConnector
from .static import StaticConnector
from .tee import TeeConnector
from .youtube import YouTubeConnector
from .zone import MailConnector, ZoneConnector

CONNECTORS = {
    "github_repo": GitHubConnector(),
    "domain": DomainConnector(),
    "website": WebsiteConnector(),
    "app_store": AppStoreConnector(),
    "social": SocialConnector(),
    "postiz_social": PostizConnector(),
    "static": StaticConnector(),
    "browser": BrowserConnector(),
    "local_artifact": LocalArtifactConnector(),
    "registrar": RegistrarConnector(),
    "zone": ZoneConnector(),
    "mail": MailConnector(),
    "names": NamesConnector(),
    "number": PhoneConnector(),
    "publisher": PublisherConnector(),
    "inbox": InboxConnector(),
    "youtube": YouTubeConnector(),
    "tee": TeeConnector(),
}


def register_connector(kind: str, connector) -> None:
    """Extensibility hook: external packs (freaktown, etsysignal, future
    products) register a new resource kind without forking core.

    Overwrites are rejected to keep the spine stable — a changed behaviour
    is a new kind, mirroring the QP gate-versioning rule.
    """
    if not kind or not isinstance(kind, str):
        raise ValueError("kind must be a non-empty string")
    if kind in CONNECTORS:
        raise ValueError(f"connector kind {kind!r} already registered")
    if not hasattr(connector, "observe"):
        raise ValueError("connector must implement observe(desired)")
    CONNECTORS[kind] = connector


def get_connector(kind: str):
    return CONNECTORS.get(kind)


def list_connector_kinds() -> list[str]:
    return sorted(CONNECTORS)
