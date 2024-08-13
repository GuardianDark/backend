import json
import os
import secrets
from datetime import datetime
import codecs

class UserManager:
    def __init__(self):
        self.users_file = 'data/users.json'
        self.load_users()
        self.chat_manager = ChatManager(self)


    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as file:
                self.users = json.load(file)
        else:
            self.users = {}

    def save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as file:
            json.dump(self.users, file, ensure_ascii=False, indent=4)

    def add_user(self, username, phone, fullname, bio, profile=None):
        default_profile = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRFEZSqk8dJbB0Xc-fr6AWv2aocxDdFpN6maQ&'

        if profile is None or profile.strip() == '':
            profile = default_profile
        
        if username not in self.users:
            auth_token = self.generate_auth_token()
            self.users[username] = {
                "phone": phone,
                "fullname": fullname,
                "status": "online",
                "bio": bio,
                "profile": profile,
                "token": auth_token
            }
            self.save_users()

            self.chat_manager.initialize_user_messages(username)

            return {
                'status': 'OK',
                'user': self.users[username]
            }
        return {
            'status': 'USERNAME_INVALID'
        }
    
    def update_profile(self, username, auth_token, fullname=None, bio=None, profile=None):
            user = self.users.get(username)
            if user and user['token'] == auth_token:
                if fullname:
                    user['fullname'] = fullname
                if bio:
                    user['bio'] = bio
                if profile:
                    user['profile'] = profile
                self.save_users()
                return {'status': 'OK', 'user': user}
            else:
                return {'status': 'TOKEN_INVALID | NOT_FOUND', 'user': {}}
            
    def online(self, username, auth_token, status = 'offline'):
            user = self.users.get(username)
            if user and user['token'] == auth_token:
                if status:
                    user['status'] = status
                self.save_users()
                return {'status': 'OK', 'user': user}
            else:
                return {'status': 'TOKEN_INVALID | NOT_FOUND', 'user': {}}       
             
    def authenticate_user(self, username, auth_token):
        user = self.users.get(username)
        if user:
            if user['token'] == auth_token:
                return {'status': 'OK', 'user': user}
            else:
                return {'status': 'TOKEN_INVALID', 'user': {}}
        else:
            return {'status': 'NOT_FOUND', 'user': {}}

    def login(self, username, auth_token, phone_number):
        user = self.users.get(username)
        if user:
            if user['token'] == auth_token and user['phone'] == phone_number:
                return {'status': 'OK', 'user': user}
            else:
                return {'status': 'TOKEN_INVALID', 'user': {}}
        else:
            return {'status': 'NOT_FOUND', 'user': {}}
    
    def getUsernameByID(self, username, auth_token, getUser):
        if self.authenticate_user(username=username, auth_token=auth_token).get('status') not in ['TOKEN_INVALID', 'NOT_FOUND']:
            if self.users.get(getUser):
                user = self.users.get(getUser)
                return {'status': 'OK', 'user': {'fullname': user['fullname'], 'bio': user['bio'], 'username': getUser, 'profile': user['profile'], 'status': user['status'], 'admin': user['very']}}
            else:
                return {'status': 'USER_NOT_FOUND', 'user': {}}
        else:
            return {'status': 'TOKEN_INVALID | NOT_FOUND', 'user': {}}

    def generate_auth_token(self):
        return secrets.token_urlsafe()

    def user_exists(self, username):
        return username in self.users
    
    def add_group_message(self, from_user, group_name, message, timestamp=None, message_id=None):
        return self.group_manager.add_group_message(from_user, group_name, message, timestamp, message_id)

    def add_member_to_group(self, group_name, username):
        return self.group_manager.add_member_to_group(group_name, username)

    def remove_member_from_group(self, group_name, username):
        return self.group_manager.remove_member_from_group(group_name, username)

    def get_group_info(self, group_name):
        return self.group_manager.get_group_info(group_name)
    

class ChatManager:
    def __init__(self, user_manager):
        self.user_manager = user_manager
        self.messages = self.load_messages('data/private_messages.json')
        self.groups = self.load_messages('data/gruops.json')
        self.message_id_counter = self.load_message_id_counter()


    def increment_unread_message_count(self, to_user, from_user):
        users_list = self.messages[to_user]["listPrivate"]["userslist"]
        for user in users_list:
            if user["username"] == from_user:
                user["count_message"] = user.get("count_message", 0) + 1
                break
        else:
            new_user = {
                "username": from_user,
                "last_message": "",
                "last_time": "",
                "count_message": 1
            }
            users_list.insert(0, new_user)
        self.save_messages('data/private_messages.json')

    def reset_unread_message_count(self, username, target_user):
        users_list = self.messages[username]["listPrivate"]["userslist"]
        for user in users_list:
            if user["username"] == target_user:
                user["count_message"] = 0
                break
        self.save_messages('data/private_messages.json')

    def getUserList(self, username, auth_token):
        if self.user_manager.authenticate_user(username=username, auth_token=auth_token).get('status') not in ['TOKEN_INVALID', 'NOT_FOUND']:
            users_list = self.messages.get(username, {}).get('listPrivate', {}).get('userslist', [])
            enriched_users_list = []
            for user in users_list:
                user_profile = self.user_manager.users.get(user['username'], {}).get('profile', "default_profile_url")
                user_status = self.user_manager.users.get(user['username'], {}).get('status', "offline"),
                admin = self.user_manager.users.get(user['username'], {}).get('very', "user"),
                enriched_user = {
                    "username": user['username'],
                    "last_message": user['last_message'],
                    "last_time": user['last_time'],
                    "profile": user_profile,
                    "count_message": user['count_message'],
                    "status": user_status[0],
                    "admin": admin[0]
                }
                enriched_users_list.append(enriched_user)

            return {'status': 'OK', 'users': enriched_users_list}
        else:
            return {'status': 'TOKEN_INVALID | NOT_FOUND', 'user': {}}
        
    def getMessages(self, username, auth_token, user):
        if self.user_manager.authenticate_user(username=username, auth_token=auth_token).get('status') not in ['TOKEN_INVALID', 'NOT_FOUND']:
            user_messages = self.messages.get(username, {}).get('listPrivate', {}).get('message', {}).get(user, {})
            response = json.dumps({'status': 'OK', 'users': user_messages}, ensure_ascii=False)
            return response
        else:
            return json.dumps({'status': 'TOKEN_INVALID | NOT_FOUND', 'user': {}})
        
    def initialize_user_messages(self, username):
        if username not in self.messages:
            self.messages[username] = {
                "joinGroup": [],
                "listPrivate": {
                    "userslist": [],
                    "message": {}
                }
            }
            self.save_messages('data/private_messages.json')

    def edit_message(self, username, token, message_id, to_user, new_message):
        auth_response = self.user_manager.authenticate_user(username=username, auth_token=token)
        if auth_response.get('status') in ['TOKEN_INVALID', 'NOT_FOUND']:
            return {'status': 'TOKEN_INVALID | NOT_FOUND'}
        
        user_messages = self.messages.get(username, {}).get('listPrivate', {}).get('message', {}).get(to_user, {})
        if message_id not in user_messages:
            return {'status': 'MESSAGE_NOT_FOUND'}

        user_messages[message_id]['message'] = new_message
        user_messages[message_id]['isEdit'] = True

        reverse_message = self.messages.get(to_user, {}).get('listPrivate', {}).get('message', {}).get(username, {})
        if message_id in reverse_message:
            reverse_message[message_id]['message'] = new_message
            reverse_message[message_id]['isEdit'] = True

        for user in self.messages[username]['listPrivate']['userslist']:
            if user['username'] == to_user:
                user['last_message'] = new_message
                break

        for user in self.messages[to_user]['listPrivate']['userslist']:
            if user['username'] == username:
                user['last_message'] = new_message
                break

        self.save_messages('data/private_messages.json')

        return {'status': 'OK', 'message': 'editMessage'}


    def add_private_message(self, from_user, to_user, message, timestamp=None, message_id=None, reply_data=None):
        if self.messages is None:
            self.messages = {}

        if not self.user_manager.user_exists(to_user):
            print(f"User {to_user} does not exist. Message not sent.")
            return

        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")

        if message_id is None:
            message_id = str(self.message_id_counter)
            self.message_id_counter += 1
            self.save_message_id_counter()

        if from_user not in self.messages:
            self.initialize_user_messages(from_user)

        if to_user not in self.messages:
            self.initialize_user_messages(to_user)

        if to_user not in self.messages[from_user]["listPrivate"]["message"]:
            self.messages[from_user]["listPrivate"]["message"][to_user] = {}

        if from_user not in self.messages[to_user]["listPrivate"]["message"]:
            self.messages[to_user]["listPrivate"]["message"][from_user] = {}

        message_data = {
            "username": from_user,
            "from_chat": from_user,
            "to_chat": to_user,
            "message": message,
            "time": timestamp,
            "message_id": message_id,
            "reply": reply_data
        }

        self.messages[from_user]["listPrivate"]["message"][to_user][message_id] = message_data

        self.messages[to_user]["listPrivate"]["message"][from_user][message_id] = message_data

        self.update_user_list(from_user, to_user, message, timestamp)
        self.update_user_list(to_user, from_user, message, timestamp)
        self.increment_unread_message_count(to_user, from_user)
        self.save_messages('data/private_messages.json')


    def update_user_list(self, current_user, chat_user, message, timestamp):
        users_list = self.messages[current_user]["listPrivate"]["userslist"]

        existing_user = next((user for user in users_list if user["username"] == chat_user), None)
        
        if existing_user:
            existing_user["last_message"] = message
            existing_user["last_time"] = timestamp
            
            user_index = users_list.index(existing_user)
            self.move_to_front(users_list, user_index)
        else:
            new_user = {
                "username": chat_user,
                "last_message": message,
                "last_time": timestamp
            }
            users_list.insert(0, new_user)

    def move_to_front(self, lst, index):
        if index is not None and index < len(lst):
            item = lst.pop(index)
            lst.insert(0, item)

    def save_messages(self, file_path):
        with codecs.open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.messages, file, ensure_ascii=False, indent=4)

    def load_messages(self, file_path):
        try:
            with codecs.open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return {}

    def load_message_id_counter(self):
        if os.path.exists('data/message_id_counter.json'):
            with codecs.open('data/message_id_counter.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        return 1

    def save_message_id_counter(self):
        with codecs.open('data/message_id_counter.json', 'w', encoding='utf-8') as file:
            json.dump(self.message_id_counter, file, ensure_ascii=False, indent=4)

class GroupManager:
    def __init__(self, user_manager):
        self.user_manager = user_manager
        self.groups = self.load_groups('data/groups.json')
        self.message_id_counter = self.load_message_id_counter()

    def load_groups(self, file_path):
        try:
            with codecs.open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return {}

    def save_groups(self, file_path):
        with codecs.open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.groups, file, ensure_ascii=False, indent=4)

    def load_message_id_counter(self):
        if os.path.exists('data/message_id_counter.json'):
            with codecs.open('data/message_id_counter.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        return 1

    def save_message_id_counter(self):
        with codecs.open('data/message_id_counter.json', 'w', encoding='utf-8') as file:
            json.dump(self.message_id_counter, file, ensure_ascii=False, indent=4)

    def add_group_message(self, from_user, group_name, message, timestamp=None, message_id=None):
        if group_name not in self.groups:
            print(f"Group {group_name} does not exist.")
            return

        if not self.user_manager.user_exists(from_user):
            print(f"User {from_user} does not exist. Message not sent.")
            return

        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")

        if message_id is None:
            message_id = str(self.message_id_counter)
            self.message_id_counter += 1
            self.save_message_id_counter()

        if group_name not in self.groups:
            self.groups[group_name] = {
                "usernameGroup": group_name,
                "members": [],
                "onlines": [],
                "profile": "default_profile_url",
                "bio": "",
                "message": {},
                "last": {
                        "username": "CipherX",
                        "message": "به لند گرام خوش آمدید",
                        "time": "00:00",
                        "message_id": 0000000
                }
            }

        if message_id not in self.groups[group_name]["message"]:
            self.groups[group_name]["message"][message_id] = {
                "username": from_user,
                "from": from_user,
                "to": group_name,
                "image": self.user_manager.users.get(from_user)['profile'],
                "message": message,
                "time": timestamp,
                "message_id": message_id
            }

        self.groups[group_name]["last"] = {
            "username": from_user,
            "message": message,
            "time": timestamp,
            "message_id": message_id
        }

        self.save_groups('data/groups.json')

    def add_member_to_group(self, group_name, username):
        if group_name in self.groups:
            if username not in self.groups[group_name]["members"]:
                self.groups[group_name]["members"].append(username)
                self.save_groups('data/groups.json')
                return {'status': 'OK'}
            else:
                return {'status': 'USER_ALREADY_MEMBER'}
        else:
            return {'status': 'GROUP_NOT_FOUND'}
        
    def get_members_group(self, group_name, username, token):
        if self.user_manager.authenticate_user(username=username, auth_token=token).get('status') not in ['TOKEN_INVALID', 'NOT_FOUND']:
            if group_name in self.groups:
                if username not in self.groups[group_name]["members"]:
                    return {'status': 'ERROR_YOU_NOT_JOIN'}
                else:
                    members = self.groups[group_name]["members"]
                    member_info = []

                    for member in members:
                        user_info = self.user_manager.getUsernameByID(username, token, member) 
                        if user_info['status'] == 'OK':
                            member_info.append({
                                'username': member,
                                'fullname': user_info['user']['fullname'],
                                'profile': user_info['user']['profile'],
                                'status': user_info['user']['status']
                            })

                    return {'status': 'OK', 'members': member_info}
            else:
                return {'status': 'GROUP_NOT_FOUND'}
        else: return {'status': 'TOKEN_USERNAME_INVAILD'}

    def remove_member_from_group(self, group_name, username):
        if group_name in self.groups:
            if username in self.groups[group_name]["members"]:
                self.groups[group_name]["members"].remove(username)
                self.save_groups('data/groups.json')
                return {'status': 'OK'}
            else:
                return {'status': 'USER_NOT_FOUND'}
        else:
            return {'status': 'GROUP_NOT_FOUND'}

    def get_group_info(self, username, token,group_name):
        if self.user_manager.authenticate_user(username=username, auth_token=token).get('status') not in ['TOKEN_INVALID', 'NOT_FOUND']:
            if group_name in self.groups:
                group = self.groups[group_name];
                return {'status': 'OK', 'group': {'username': group['usernameGroup'], 'profile': group['profile']}}
            else:
                return {'status': 'GROUP_NOT_FOUND'}

    def get_all_groups(self):
        return self.groups

    def get_group_messages(self, group_name):
        if group_name in self.groups:
            return self.groups[group_name]["message"]
        else:
            return {}
