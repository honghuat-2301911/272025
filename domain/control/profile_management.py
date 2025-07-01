from data_source.user_queries import (
    remove_user_profile_picture,
    update_user_profile_by_id,
)


class ProfileManagement:
    def updateProfile(self, user_id, name, password, profile_picture=None):
        if profile_picture is not None:
            return update_user_profile_by_id(user_id, name, password, profile_picture)
        else:
            return update_user_profile_by_id(user_id, name, password)

    def removeProfilePicture(self, user_id):
        return remove_user_profile_picture(user_id)
