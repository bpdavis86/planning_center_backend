# planning_center_backend

This is a requests backend provider for the Planning Center website.
It provides missing functionality for adding and editing groups which is not yet in the official API.

# Basic Use:

All access to the website is provided 
through the `planning_center_backend.planning_center.PlanningCenterBackend` object.
This object serves as the attachment point for multiple API sub-nodes which may be used to access
the various functionality once login is performed.

## Login:
To login to the website, use the `PlanningCenterBackend.login` method. An example is shown below.

```python
from planning_center_backend import planning_center

username = 'my_user'
password = 'my_password'

backend = planning_center.PlanningCenterBackend()
success = backend.login(username, password)

if success:
    print('Successfully logged in!')
else:
    print('Failed to log in')
```

The `PlanningCenterBackend.logged_in` field reflects the current login status.

To log out, use `PlanningCenterBackend.logout()`.

## Querying People
The `PlanningCenterBackend.people` field provides access to the main people API.
The method `people.query()` provides query access to the API.
There are two ways this query can be performed, using a simple name query, or
by adding advanced search filter parameters.

To do a simple name query, simply pass a string:
```python
# assume logged in already

people_data = backend.people.query('John Smith')
```
In this case, all people with name match "John Smith" will be returned.

The `planning_center_backend.people.PeopleQueryExpression` object provides advanced functionality.
For example, here we will search for a John Smith who is Male and a site admin.

```python
from planning_center_backend.people import PeopleQueryExpression

query_expr = PeopleQueryExpression(
    search_name="John Smith", 
    gender='M', 
    site_administrator=True
)
people_data = backend.people.query(query_expr)
```

All people have an associated id (primary key) in the Planning Center database.
This id is returned as part of the query response. For example

```python
people_data = backend.people.query('John Smith')
# assume the first John Smith is who we want
person = people_data[0]
person_id = person.id
```

If we know this id, we can use it to get the person's record directly using the `get` method rather than querying.
```python
person = backend.people.get(person_id)
```
This retrieves the same data record as above.

A lot of relevant details of the person are included in the record result, including
birthday, admin status, creation time, etc. 
This data is available on the `attributes` field of the person object.

```python
people_data = backend.people.query('John Smith')
# assume the first John Smith is who we want
person = people_data[0]
# get John's birthday
birthday = person.attributes.birthdate
```

## Managing Groups
The `PlanningCenterBackend.groups` field provides access to the groups API functionality.

### Creating a Group
To create a group, use the `create()` method, passing the name and optional group type.
Group types are provided in the `planning_center_backend.groups.GroupType` enum. 
The default type is SmallGroup.
```python
# create a new small group
my_group = backend.groups.create('My Group')
```

```python
# create an online group
from planning_center_backend.groups import GroupType

my_group = backend.groups.create('My Group', GroupType.Online)
```

The create method returns a group API object that may be used to manipulate the group.

### Querying Existing Groups
API objects for existing groups may also be retrieved using the `query` method.
Groups may be filtered by name, or if the name is omitted, all groups will be returned.
```python
# Query a specific group
# a list is returned, here we get the first match
# if the group is not found, this would fail
my_group, *_ = backend.groups.query('My Existing Group')
```
```python
# Query all groups
all_groups = backend.groups.query()
```

If the numeric group identifier is known, the `get` method may be used to get the API object directly.
(If on the website, the group id is the number after `groups/` in the URL, 
i.e. 1234 in 'https://groups.planningcenteronline.com/groups/1234/members)
)
```python
# Get a specific group by id
my_group = backend.groups.get(1234)
```

### Modifying a Group's Settings
Once a group API object has been retrieved via either creation, query, or get methods,
one can manipulate this object to configure the group.

The most basic interaction with the group is to change settings such as description, name, location, etc.
Most settings are exposed as properties on the Group API object.
Here are some basic examples of reading and writing these properties.
```python
from planning_center_backend.groups import GroupObject, GroupType
my_group: GroupObject = backend.groups.get(1234)

# Read properties
old_name = my_group.name
old_description = my_group.description

# Write properties
# Change name
my_group.name = 'Better Name'
# Add/change description
# The description is provided in an HTML box in the website, thus the <div>
# presumably other HTML formatting is valid here
my_group.description = '<div>New Description</div>'
my_group.schedule = 'Every Friday'
# reset the group type
my_group.group_type = GroupType.SmallGroup
my_group.contact_email = 'john.smith@foo.com'
```

There is a large list of setting properties and not all are demonstrated here.
Refer to the `planning_center_backend.groups.GroupObject` documentation for a full listing.
Most things that can be configured through the website settings page are implemented.
Some values may be read-only.

### Managing Auto-Refresh
In order to keep the cached group information up to date with the website, every time a
group property is changed, all group data is reloaded from the web.
If the user wishes to change many properties at once in his code, this may not be 
desirable behavior from a performance standpoint.
The auto-refresh behavior can be managed using the `auto_refresh` property of the GroupObject.

```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject = backend.groups.get(1234)

# Write several properties without auto-refresh
my_group.auto_refresh = False
my_group.name = 'Better Name'
my_group.description = '<div>New Description</div>'
my_group.schedule = 'Every Friday'
# turn back on auto refresh
my_group.auto_refresh = True
```

A context manager `no_refresh` is also provided to assist with this behavior.
This manager disables refresh in the block and returns it to its original setting outside the block.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject = backend.groups.get(1234)

# Write several properties without auto-refresh
with my_group.no_refresh():
    my_group.name = 'Better Name'
    my_group.description = '<div>New Description</div>'
    my_group.schedule = 'Every Friday'
    
# refresh is restored here
assert my_group.name == 'Better Name'
```

Refresh can be manually performed while auto-refresh is disabled using the `refresh` method.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject = backend.groups.get(1234)

# Write several properties without auto-refresh
with my_group.no_refresh():
    my_group.name = 'Better Name'
    my_group.refresh()
    # using the new name here
    my_group.description = f'<div>{my_group.name} New Description</div>'

```

### Managing Group Members
To add a group member, first look up the member's id using the people API.
Then the person can be added to the group using `add_member`.

```python
from planning_center_backend.groups import GroupObject

member_data = backend.query.people('John Smith')
if not member_data:
    # did not find the person
    raise ValueError
# assume first query result is correct
member_id = member_data[0].id

# Add the person to the group
my_group: GroupObject = backend.groups.get(1234)
my_group.add_member(member_id)
```
Members can be set as leader, and email notification of the membership can be enabled via appropriate flags.
```python
my_group.add_member(member_id, leader=True, notify=True)
```

An existing member list can be retrieved via the `memberships` property.
This property returns a list of API query object results representing the group members.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

members = my_group.memberships
for member in members:
    # print a list of member names by id
    print(f'Group Member {member.id}: {member.attributes.first_name} {member.attributes.last_name}')
```

A particular member's membership information can be retrieved with `get_member` by supplying their Person id.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

this_member = my_group.get_member(member_person_id)
```

The member's permissions can be updated with `update_member` using their Person id.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

# make this person a new leader
my_group.update_member(new_leader_id, leader=True)
# allow this person to take attendance and notify him of change
my_group.update_member(new_attendance_taker_id, attendance_taker=True, notify=True)
```

Members can be removed with `delete_member` (also using Person id).
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

# remove this member 
my_group.delete_member(former_member_id)
# remove this member and notify him via email
my_group.delete_member(former_member_id_2, notify=True)
# remove this person and do not error even if not in the group
my_group.delete_member(former_member_id_3, missing_ok=True)
```

### Managing Group Tags
To add/remove tags in a group, the tag id must first be identified.
The available tags may be queried using `groups.tag.query()` on the Group API provider.

```python
from planning_center_backend.planning_center import PlanningCenterBackend

backend: PlanningCenterBackend

# find the tag corresponding to meeting on Sunday
result = backend.groups.tags.query('Sunday')
if not result:
    # we didn't find the tag we want
    raise ValueError
# assume first result is correct
sunday_tag = result[0]
sunday_tag_id = tag.id
```
```python
# get a list of all tags
all_tags = backend.groups.tags.query()
```

At this time, new tag creation is not supported and should be performed manually through the website.

To view which tags are currently assigned to a group, use the `tags` property of the group object.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

for tag in my_group.tags:
    print(f'Group Tag: {tag.attributes.name}')
```

To add a tag, you can use either numeric tag id (int), tag name (str) or TagData object returned from query. 
```python
from planning_center_backend.groups import GroupObject
from planning_center_backend.planning_center import PlanningCenterBackend

backend: PlanningCenterBackend
my_group: GroupObject

result = backend.groups.tags.query('Sunday')
sunday_tag = result[0]
sunday_tag_id = tag.id

# all equivalent methods of adding Sunday tag
my_group.add_tag(sunday_tag_id)
# this will only work if querying the name Sunday has exactly one match
my_group.add_tag('Sunday')
my_group.add_tag(sunday_tag)
```

You can check if a group has a given tag in a similar way, by int id, str name, or TagData object
```python
# all equivalent methods of querying Sunday tag
has_sunday_tag = my_group.has_tag(sunday_tag_id)
# this will only work if querying the name Sunday has exactly one match
has_sunday_tag = my_group.has_tag('Sunday')
has_sunday_tag = my_group.has_tag(sunday_tag)
```

Deleting a tag is done analogously using `delete_tag`.
The default is to silently ignore a tag that does not exist.
```python
# all equivalent methods of querying Sunday tag
my_group.delete_tag(sunday_tag_id)
# in this case, throw error if the tag did not exist
my_group.delete_tag('Sunday', missing_ok=False)
my_group.delete_tag(sunday_tag)
```

### Managing Group Location
Group location management is somewhat complex because locations include latitude and longitude data.
On the website, this is provided via a Google Maps API integration.
If the user wishes to provide similar functionality (address lookup via Google Maps), 
he should create a Google Maps account and set up an API key.

To query all locations available for a group to use, use `locations.query` on the group object.
(Some locations are shared between groups and some are group-specific.)

```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

# Print address of all available locations
for loc in my_group.locations.query():
    print(f'Location {loc.name} ({loc.id}) Address: {loc.formatted_address}')
```

Note that this API is a v1 API, so there is no "attributes" object, all the location attributes
are simply on the base query result. Location id is found in the `id` field of the query result.

Unfortunately, there is no way to filter queries in the request.
Neither is there a way to retrieve one record by location id.
Therefore, the developer is cautioned to use this query feature wisely and cache results as possible
in order to maintain performance.

The current location id is given by the `location_id` field for the group.
To set a new location, set the location id.

```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

# query all locations
all_locations = my_group.locations.query()
# find the desired location in query result
desired_location_name = "Joe's House"
desired_location = [_ for _ in all_locations if _.name == desired_location_name][0]
# set the new location
my_group.location_id = desired_location.id
```

To create a new location for the Group, there are two methods, a location
based on Google Maps API query result, or a custom location (with manual latitude and longitude).
To facilitate this, a Google Maps API stub integration is provided.

```python
from planning_center_backend.maps import Maps
from planning_center_backend.groups import GroupObject
my_group: GroupObject

maps = Maps(api_key='your_google_api_key')

places = maps.find_place_from_text('Empire State Building')
# assume first result is what you want
place = places[0]
geocodes = maps.geocode_from_place_id(place.place_id)
# again, assume first result is correct
geocode = geocodes[0]

location_id = my_group.locations.create(
    name='Empire State Building',
    geocode_data=geocode,
    shared=True, # allow sharing with other groups
)

# assign this new location to the group
my_group.location_id = location_id
```

Alternatively, if the latitude and longitude are known, one can use custom location without Google API.
```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

location_id = my_group.locations.create_custom(
    name='Empire State Building',
    formatted_address='20 W 34th St., New York, NY 10001',
    latitude=40.74850,
    longitude=-73.98566,
    shared=True, # allow sharing with other groups
)

# assign this new location to the group
my_group.location_id = location_id
```

Note that creating a new location does not assign it as the group location, it only adds it to list of
available group locations.

To delete a group location, use `locations.delete` with the location id.

```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

old_location_id = my_group.location_id
my_group.location_id = new_location_id

# delete the old location
my_group.locations.delete(old_location_id)
```

### Managing Group Events

Group events are currently only read-only accessible.
Creating and managing events may be available in a future version.

To view all current group events, use the `events` property.

```python
from planning_center_backend.groups import GroupObject
my_group: GroupObject

# Show all group event names and start times
for event in my_group.events:
    print(f'{event.attributes.name} at {event.attributes.starts_at}')
```
