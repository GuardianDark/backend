from utlis.encrypt import CryptoServer
from db.manager import ChatManager, UserManager, GroupManager
import logging, random
from datetime import datetime
import pytz, json, codecs

class Handler:
    def __init__(self, chatManager: ChatManager, userManager: UserManager) -> None:
        self.chatManager  = chatManager
        self.userManager  = userManager
        self.groupManager = GroupManager(user_manager=userManager)
    
    def getUserInfo(self, username: str, token: str):
        return self.userManager.authenticate_user(username=username, auth_token=token)
    
    def login(self, username: str, token: str, phone_number):
        return self.userManager.login(username=username, auth_token=token, phone_number=phone_number)
    
    def getUsernameByID(self, username: str, token: str, getUser: str):
        return self.userManager.getUsernameByID(username=username, auth_token=token, getUser=getUser)
    
    def getGroupByID(self, username: str, token: str, group_name: str):
        return self.groupManager.get_group_info(username=username, token=token, group_name=group_name)   
    
    def getChats(self, username: str, token: str):
        return self.chatManager.getUserList(username=username, auth_token=token)
    
    def getMembersList(self, username: str, token: str, group_name: str):
        return self.groupManager.get_members_group(username=username, token=token, group_name=group_name)    
    
    def editMessages(self, username: str, token: str, to: str, message_id: str, newMessage: str):
        print(f"TO {to}, message_id : {message_id}, newMessage: {newMessage}")
        return self.chatManager.edit_message(username=username, token=token, message_id=message_id, new_message=newMessage, to_user=to)
    
    def getMessages(self, username: str, token: str, user: str):
        return self.chatManager.getMessages(username=username, auth_token=token, user=user)
    
    def update_profile(self, username, token, data):
            return self.userManager.update_profile(
                username=username,
                auth_token=token,
                fullname=data.get('fullname'),
                bio=data.get('bio'),
                profile=data.get('profile')
            )
    def register(self, username: str, phone_number: str, fullname: str, profile=None):
        default_profile = 'https://www.google.com/url?sa=i&url=https%3A%2F%2Fstock.adobe.com%2Fimages%2Fdefault-avatar-profile-flat-icon-social-media-user-vector-portrait-of-unknown-a-human-image%2F353110097&psig=AOvVaw3CkGCCeJAqiqKqgZ_mMS0G&ust=1722945658368000&source=images&cd=vfe&opi=89978449&ved=0CBEQjRxqFwoTCNie4Ojm3YcDFQAAAAAdAAAAABAK'
    
        if profile is None or profile.strip() == '':
            profile = default_profile
        
        return self.userManager.add_user(username=username, phone=phone_number, bio='', fullname=fullname, profile=profile)
        
    def mark_messages_as_read(self, username, token, target_user):
        if self.userManager.authenticate_user(username=username, auth_token=token).get('status') == 'OK':
            self.chatManager.reset_unread_message_count(username, target_user)
            return {'status': 'OK'}
        else:
            return {'status': 'TOKEN_INVALID | NOT_FOUND'}
        
    def getChatsGroup(self, username: str, token: str):
        auth_response = self.userManager.authenticate_user(username=username, auth_token=token)
        if auth_response.get('status') != 'OK':
            return {'status': 'TOKEN_INVALID | NOT_FOUND'}

        try:
            with open('data/private_messages.json', 'r') as file:
                private_messages_data = json.load(file)
            
            user_groups = private_messages_data.get(username, {}).get('joinGroup', [])
        except Exception as e:
            logging.error(f"Error reading private_messages.json: {str(e)}")
            return {'status': 'ERROR', 'message': 'Error reading private messages data'}

        try:
            with codecs.open('data/groups.json', 'r', encoding='utf-8') as file:
                groups_data = json.load(file)
            
            group_data = {}
            for group in user_groups:
                if group in groups_data:
                    if 'last' not in groups_data[group]:
                        groups_data[group]['last'] = {
                            "username": "CipherX",
                            "message": "خوش اومدید به لند گرام",
                            "time": "00:00",
                            "message_id": 2697917
                        }
                    group_data[group] = {
                        'profile': groups_data[group]['profile'],
                        'bio': groups_data[group]['bio'],
                        'last_message': groups_data[group]['last']
                    }
                    
            return {'status': 'OK', 'data': group_data}
        
        except Exception as e:
            logging.error(f"Error reading groups.json: {str(e)}")
            return {'status': 'ERROR', 'message': 'Error reading groups data'}
        
    def getGroupMessages(self, username: str, token: str, group_name: str):
        if self.userManager.authenticate_user(username=username, auth_token=token).get('status') == 'OK':
            return {'status': 'OK', 'data': self.groupManager.get_group_messages(group_name=group_name)}
        else:
            return {'status': 'TOKEN_INVALID | NOT_FOUND'}         
           
    def methodNum(self, method: str, data: dict, hash: CryptoServer):
        try:
            match method:
                case 'editMessage':
                    return {"data_enc": self.editMessages(username=data['username'], token=data['token'], to=data['to'], message_id=data['message_id'], newMessage=data['newMessage'])}
                case 'getUserInfo':
                    return {"data_enc": self.getUserInfo(username=data['username'], token=data['token'])}
                case 'getMemberGroup':
                    return {"data_enc": self.getMembersList(username=data['username'], token=data['token'], group_name=data['group_name'])}               
                case 'getChats':
                    return {"data_enc": hash.encrypt(str(self.getChats(username=data['username'], token=data['token'])))}
                case 'register':
                    return {"data_enc": hash.encrypt(str(self.register(username=data['username'], phone_number=data['phone_number'], fullname=data['fullname'], profile=data.get('profile'))))}
                case 'login':
                    return {"data_enc": self.login(username=data['username'], phone_number=data['phone_number'], token=data['token'])}               
                case 'getUsernameByID':
                    return {"data_enc": self.getUsernameByID(username=data['username'], token=data['token'], getUser=data['getUser'])}
                case 'getGroupByID':
                    return {"data_enc": self.getGroupByID(username=data['username'], token=data['token'], group_name=data['group_name'])}
                case 'getMessages':
                    return {"data_enc": hash.encrypt(str(self.getMessages(username=data['username'], token=data['token'], user=data['user'])))}
                case 'updateProfile':
                    return {"data_enc": self.update_profile(username=data['username'], token=data['token'], data=data['update_data'])}
                case _:
                    return {
                        'status': 'ERROR',
                        'message': 'METHOD_INVALID'
                    }
        except Exception as e:
            logging.error(f"Error in methodNum: {str(e)}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def handle_send_message(self, data):
        try:
            from_user = data.get('from')
            to_user = data.get('to')
            message = data.get('message')
            reply_data = data.get('reply', None)

            timestamp = datetime.now(pytz.timezone('Asia/Tehran')).strftime("%H:%M")
            message_id = random.randint(1000, 9000000)

            self.chatManager.add_private_message(from_user, to_user, message, timestamp, message_id, reply_data)

            return {
                'status': 'success',
                'data': {
                    'from': from_user,
                    'to': to_user,
                    'message': message,
                    'timestamp': timestamp,
                    'message_id': message_id,
                    'reply': reply_data
                }
            }
        except Exception as e:
            logging.error(f"Error in handle_send_message: {str(e)}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }

    def handle_send_group_message(self, data):
        try:
            from_user = data.get('from')
            group_name = data.get('group')
            message = data.get('message')

            timestamp = datetime.now(pytz.timezone('Asia/Tehran')).strftime("%H:%M")
            message_id = random.randint(1000, 9000000)

            self.groupManager.add_group_message(from_user, group_name, message, timestamp, message_id)

            return {
                'status': 'success',
                'data': {
                    'from': from_user,
                    'group': group_name,
                    'message': message,
                    'timestamp': timestamp,
                    'message_id': message_id
                }
            }
        except Exception as e:
            logging.error(f"Error in handle_send_group_message: {str(e)}")
            return {
                'status': 'ERROR',
                'message': str(e)
            }