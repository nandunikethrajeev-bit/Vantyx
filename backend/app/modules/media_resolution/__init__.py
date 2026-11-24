"""VANTYX Source & Authorized Media Resolution Subsystem.

Provides modular providers for:
1. YouTube metadata resolution (oEmbed / YouTube Data API v3).
2. Creator identity resolution & verification.
3. Authorized original media resolution (creator vaults, asset mappings, cloud storage, local staged assets).
4. Source eligibility & commercial rights evaluation (M10.1).
"""

from app.modules.media_resolution.metadata_provider import (
    MetadataProviderInterface,
    YouTubeOEmbedMetadataProvider,
    YouTubeDataApiMetadataProvider,
    CompositeMetadataProvider,
    get_metadata_provider,
)
from app.modules.media_resolution.creator_provider import (
    CreatorIdentityProviderInterface,
    DatabaseCreatorIdentityProvider,
    get_creator_provider,
)
from app.modules.media_resolution.media_resolver import (
    AuthorizedMediaResolverInterface,
    MediaResolutionResult,
    CreatorConnectedStorageResolver,
    CreatorAssetMappingResolver,
    ManifestMediaResolver,
    AuthorizedCloudStorageResolver,
    LocalStagedMediaResolver,
    OfficialPlatformApiResolver,
    CompositeAuthorizedMediaResolver,
    get_media_resolver,
    verify_media_file_integrity,
)
from app.modules.media_resolution.rights_evaluator import (
    RightsEvaluator,
    SourceEligibilityCategory,
    SourceAuthorizationResult,
)

__all__ = [
    "MetadataProviderInterface",
    "YouTubeOEmbedMetadataProvider",
    "YouTubeDataApiMetadataProvider",
    "CompositeMetadataProvider",
    "get_metadata_provider",
    "CreatorIdentityProviderInterface",
    "DatabaseCreatorIdentityProvider",
    "get_creator_provider",
    "AuthorizedMediaResolverInterface",
    "MediaResolutionResult",
    "CreatorConnectedStorageResolver",
    "CreatorAssetMappingResolver",
    "ManifestMediaResolver",
    "AuthorizedCloudStorageResolver",
    "LocalStagedMediaResolver",
    "OfficialPlatformApiResolver",
    "CompositeAuthorizedMediaResolver",
    "get_media_resolver",
    "verify_media_file_integrity",
    "RightsEvaluator",
    "SourceEligibilityCategory",
    "SourceAuthorizationResult",
]
