from planning_center_backend import planning_center
from planning_center_backend.groups import GroupIdentifier
import keyring

b = planning_center.PlanningCenterBackend()
cred = keyring.get_credential('planningcenteronline.com', None)
success = b.login(cred.username, cred.password)

if not success:
    raise ValueError('login failed')

# b.logout()

# Test Group
# g = GroupIdentifier.from_id(2037398)
# group_info = b.groups.get(g)
# print(group_info)

groups = b.groups.get_all_df()
