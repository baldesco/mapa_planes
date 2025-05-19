# app/models/__init__.py

# Import all your model classes here first
from .auth import (
    UserBase,
    UserCreate,
    User,
    UserInToken,
    SupabaseUser,
    Token,
    TokenData,
    PasswordResetRequest,
)
from .general import GeocodeResult, Msg
from .tags import TagBase, TagCreate, TagInDB, Tag
from .visits import (
    VisitBase,
    VisitCreate,
    VisitUpdate,
    VisitInDB,
    Visit,
)  # Ensure Visit is imported
from .places import (  # Ensure Place models are imported AFTER Visit if Place references Visit
    PlaceCategory,
    PlaceStatus,
    PlaceBase,
    PlaceCreate,
    PlaceUpdate,
    PlaceInDB,
    Place,
    PlaceList,
)

# --- Crucial step for Pydantic V2 with forward references ---
# After all models are defined (or imported), rebuild them to resolve forward references.
# You need to call model_rebuild() on each model that uses a forward reference
# or on models that are part of a potential circular dependency.
# It's often safest to rebuild all models that might be involved.

User.model_rebuild()
UserInToken.model_rebuild()
SupabaseUser.model_rebuild()
Token.model_rebuild()
TokenData.model_rebuild()
PasswordResetRequest.model_rebuild()

GeocodeResult.model_rebuild()
Msg.model_rebuild()

TagBase.model_rebuild()
TagCreate.model_rebuild()
TagInDB.model_rebuild()
Tag.model_rebuild()

VisitBase.model_rebuild()
VisitCreate.model_rebuild()
VisitUpdate.model_rebuild()
VisitInDB.model_rebuild()
Visit.model_rebuild()

PlaceBase.model_rebuild()
PlaceCreate.model_rebuild()
PlaceUpdate.model_rebuild()
PlaceInDB.model_rebuild()  # This is the one that has List['Visit']
Place.model_rebuild()
PlaceList.model_rebuild()

# You can also create a helper function or loop through a list of models if you have many.
# For example:
# all_models = [User, UserInToken, ..., PlaceInDB, Visit, ...]
# for model in all_models:
#     model.model_rebuild()
