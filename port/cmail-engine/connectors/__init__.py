from .appstore import AppStoreConnector
from .artifact import LocalArtifactConnector
from .browser import BrowserConnector
from .domain import DomainConnector, WebsiteConnector
from .github import GitHubConnector
from .postiz import PostizConnector
from .social import SocialConnector
from .static import StaticConnector

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
}
