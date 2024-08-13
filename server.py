import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from db.manager import GroupManager, UserManager, ChatManager
from handler.Handler import Handler
from utlis.encrypt import CryptoServer
import logging


app = Flask(__name__)
socketio = SocketIO(app)


logging.basicConfig(level=logging.INFO)

user_sessions = {}

@app.route('/api', methods=['POST'])
def api():
    try:
        data = request.get_json()
        user_manager = UserManager()
        chat_manager = ChatManager(user_manager=user_manager)
        handler = Handler(chatManager=chat_manager, userManager=user_manager)
        hash_get = CryptoServer(key=data['key'])
   
        result = handler.methodNum(method=hash_get.decrypt(data=data['method']), data=data['data'], hash=hash_get)

        if 'data_enc' in result:
            return result
        else:
            raise ValueError(result['message'])
    
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({'error': 'serverInternal', 'message': str(e)}), 500

@socketio.on('authenticate')
def handle_authenticate(data):
    try:
        username = data.get('username')
        token = data.get('token')
        user_manager = UserManager()
        
        if user_manager.authenticate_user(username=username, auth_token=token).get('status') == 'OK':
            user_sessions[username] = request.sid
            join_room(username)
            user_manager.online(username=username, auth_token=token, status='online')
            emit('authenticated', {'message': 'User authenticated', 'username': username}, to=request.sid)
        else:
            emit('authentication_failed', {'message': 'Authentication failed'}, to=request.sid)
            user_manager.online(username=username, auth_token=token, status='offline')
            logging.warning(f"Authentication failed for user {username}")
    except Exception as e:
        logging.error(f"An error occurred during authentication: {str(e)}")
        emit('error', {'message': 'Internal server error'}, to=request.sid)

@socketio.on('getChats')
def handle_get_chats(data):
    try:
        user_manager = UserManager()
        username = data.get('username')
        token = data.get('token')
        handler = Handler(chatManager=ChatManager(UserManager()), userManager=user_manager)
        
        result = handler.getChats(username=username, token=token)
        user_manager.online(username=username, auth_token=token, status='online')
        emit('chats_list', result, to=request.sid)
    except Exception as e:
        logging.error(f"Error in handle_get_chats: {str(e)}")
        emit('error', {'message': str(e)}, to=request.sid)

@socketio.on('getChatsGroup')
def handle_get_chats_group(data):
    try:
        user_manager = UserManager()
        username = data.get('username')
        token = data.get('token')
        
        handler = Handler(chatManager=ChatManager(UserManager()), userManager=user_manager)
        result = handler.getChatsGroup(username=username, token=token)
        
        if result['status'] == 'OK':
            emit('group_list', result['data'], to=request.sid)
        else:
            emit('error', {'message': result['status']}, to=request.sid)
    
    except Exception as e:
        logging.error(f"Error in handle_get_chats_group: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('getMessage')
def handle_get_messages(data):
    try:
        user_manager = UserManager()
        username = data.get('username')
        token = data.get('token')
        user = data.get('user')
        handler = Handler(chatManager=ChatManager(UserManager()), userManager=user_manager)
        
        result = handler.getMessages(username=username, token=token, user=user)
        user_manager.online(username=username, auth_token=token, status='online')
        emit('messages', result, to=request.sid)
        
    except Exception as e:
        logging.error(f"Error in handle_get_messages: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('markAsRead')
def handle_mark_as_read(data):
    try:
        user_manager = UserManager()
        username = data.get('username')
        token = data.get('token')
        target_user = data.get('target_user')
        handler = Handler(chatManager=ChatManager(UserManager()), userManager=user_manager)
        
        result = handler.mark_messages_as_read(username=username, token=token, target_user=target_user)
        user_manager.online(username=username, auth_token=token, status='online')
        emit('messages_marked_as_read', result, to=request.sid)
    except Exception as e:
        logging.error(f"Error in handle_mark_as_read: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('sendMessage')
def handle_send_private_message(data):
    user_manager = UserManager()
    chat_manager = ChatManager(user_manager=user_manager)
    handler = Handler(chatManager=chat_manager, userManager=user_manager)

    try:
        from_user = data.get('from')
        to_user = data.get('to')


        if from_user in user_sessions and to_user in user_sessions:
            result = handler.handle_send_message(data)
            
            if result['status'] == 'success':
                print(f'\033[31m|| SID :: {request.sid} || DATA ::: {data} || TO ::: {to_user} || FROM_USER ::: {from_user} || {user_sessions}')
                socketio.emit(f'receive_private_message', result['data'], room=to_user)
                socketio.emit(f'receive_private_message', result['data'], room=from_user)
            else:
                logging.error(f"Message handling error: {result['message']}")
        else:
            print(f'Offline Users {user_sessions}')
            result = handler.handle_send_message(data)
            socketio.emit(f'offline', result['data'], room=from_user, to=request.sid)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")

@socketio.on('sendGroupMessage')
def handle_send_group_message(data):
    print(f"SendMessage To group {data}")
    user_manager = UserManager()
    chat_manager = ChatManager(user_manager=user_manager)

    handler = Handler(chatManager=chat_manager, userManager=user_manager)

    try:
        from_user = data.get('from')
        group_name = data.get('group')

        if from_user in user_sessions and group_name in user_sessions:
            result = handler.handle_send_group_message(data)
            
            if result['status'] == 'success':
                for member in user_sessions:
                    socketio.emit('receive_group_message', result['data'], room=member)
            else:
                logging.error(f"Message handling error: {result['message']}")
        else:
            result = handler.handle_send_group_message(data)
            socketio.emit(f'offline', result['data'], room=from_user)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")

@socketio.on('getGroupMessages')
def handle_get_group_messages(data):
    try:
        user_manager = UserManager()
        username = data.get('username')
        token = data.get('token')
        group_name = data.get('group')
        handler = Handler(chatManager=ChatManager(UserManager()), userManager=user_manager)
        
        result = handler.getGroupMessages(username=username, token=token, group_name=group_name)
        if result['status'] == 'OK':
            emit('group_messages', result['data'], to=request.sid)
        else:
            emit('error', {'message': result['status']}, to=request.sid)
    
    except Exception as e:
        logging.error(f"Error in handle_get_group_messages: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('connect')
def handle_connect():
    logging.info(f"Client connected with SID: {request.sid}")
    emit('handshake', {'message': 'Please authenticate with username and token'}, to=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    logging.info(f"Client disconnected. SID: {request.sid}")
    for username, sid in user_sessions.items():
        if sid == request.sid:
            user_manager = UserManager()
            user_manager.online(username=username, auth_token=user_manager.users[username]['token'], status='offline')
            del user_sessions[username]
            leave_room(username)
            logging.info(f"User {username} disconnected and left room {username}")
            break

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
