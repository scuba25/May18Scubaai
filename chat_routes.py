from flask import Blueprint, request, jsonify, stream_with_context, Response
from flask_jwt_extended import jwt_required, current_user
from marshmallow import Schema, fields, ValidationError

from models import db, Conversation, Message, CustomInstruction
from services.ai_service import AIService

chat_bp = Blueprint('chat', __name__)

# Schemas for request validation
class CreateConversationSchema(Schema):
    title = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)

class SendMessageSchema(Schema):
    content = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    custom_instruction_id = fields.Int(required=False, allow_none=True)

create_conversation_schema = CreateConversationSchema()
send_message_schema = SendMessageSchema()

@chat_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for the current user."""
    conversations = Conversation.query.filter_by(user_id=current_user.id)\
                                    .order_by(Conversation.updated_at.desc())\
                                    .all()
    
    return jsonify({
        'conversations': [conv.to_dict() for conv in conversations]
    }), 200

@chat_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    """Create a new conversation."""
    try:
        data = create_conversation_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    conversation = Conversation(
        title=data['title'].strip(),
        user_id=current_user.id
    )
    
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        'message': 'Conversation created successfully',
        'conversation': conversation.to_dict()
    }), 201

@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get a specific conversation with its messages."""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    messages = Message.query.filter_by(conversation_id=conversation_id)\
                           .order_by(Message.created_at.asc())\
                           .all()
    
    return jsonify({
        'conversation': conversation.to_dict(),
        'messages': [msg.to_dict() for msg in messages]
    }), 200

@chat_bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    """Send a message in a conversation."""
    try:
        data = send_message_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    # Verify conversation belongs to user
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get custom instruction if provided
    custom_instruction = None
    if data.get('custom_instruction_id'):
        custom_instruction = CustomInstruction.query.filter_by(
            id=data['custom_instruction_id'],
            user_id=current_user.id
        ).first()
        
        if not custom_instruction:
            return jsonify({'error': 'Custom instruction not found'}), 404
    
    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        role='user',
        content=data['content']
    )
    db.session.add(user_message)
    
    # Get conversation history for context
    message_history = Message.query.filter_by(conversation_id=conversation_id)\
                                  .order_by(Message.created_at.asc())\
                                  .all()
    
    # Prepare context for AI
    context_messages = []
    for msg in message_history:
        context_messages.append({
            'role': msg.role,
            'content': msg.content
        })
    
    # Add custom instruction if available
    system_instruction = None
    if custom_instruction:
        system_instruction = custom_instruction.content
    
    try:
        # Get AI response
        ai_response = AIService.get_response(
            messages=context_messages,
            custom_instruction=system_instruction
        )
        
        # Save AI message
        ai_message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=ai_response
        )
        db.session.add(ai_message)
        
        # Update conversation timestamp
        conversation.updated_at = db.func.now()
        
        db.session.commit()
        
        return jsonify({
            'user_message': user_message.to_dict(),
            'ai_message': ai_message.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'AI service error: {str(e)}'}), 500

@chat_bp.route('/conversations/<int:conversation_id>/stream', methods=['POST'])
@jwt_required()
def stream_message(conversation_id):
    """Send a message with streaming response."""
    try:
        data = send_message_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    # Verify conversation belongs to user
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get custom instruction if provided
    custom_instruction = None
    if data.get('custom_instruction_id'):
        custom_instruction = CustomInstruction.query.filter_by(
            id=data['custom_instruction_id'],
            user_id=current_user.id
        ).first()
    
    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        role='user',
        content=data['content']
    )
    db.session.add(user_message)
    db.session.commit()
    
    # Get conversation history
    message_history = Message.query.filter_by(conversation_id=conversation_id)\
                                  .order_by(Message.created_at.asc())\
                                  .all()
    
    context_messages = []
    for msg in message_history:
        context_messages.append({
            'role': msg.role,
            'content': msg.content
        })
    
    def generate():
        try:
            full_response = ""
            system_instruction = custom_instruction.content if custom_instruction else None
            
            # Stream AI response
            for chunk in AIService.stream_response(
                messages=context_messages,
                custom_instruction=system_instruction
            ):
                full_response += chunk
                yield f"data: {chunk}\n\n"
            
            # Save complete AI message
            ai_message = Message(
                conversation_id=conversation_id,
                role='assistant',
                content=full_response
            )
            db.session.add(ai_message)
            
            # Update conversation timestamp
            conversation.updated_at = db.func.now()
            db.session.commit()
            
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: [ERROR]: {str(e)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        content_type='text/plain',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )

@chat_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a conversation and all its messages."""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    db.session.delete(conversation)
    db.session.commit()
    
    return jsonify({'message': 'Conversation deleted successfully'}), 200

@chat_bp.route('/conversations/<int:conversation_id>/title', methods=['PUT'])
@jwt_required()
def update_conversation_title(conversation_id):
    """Update conversation title."""
    try:
        data = create_conversation_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    conversation.title = data['title'].strip()
    conversation.updated_at = db.func.now()
    db.session.commit()
    
    return jsonify({
        'message': 'Conversation title updated successfully',
        'conversation': conversation.to_dict()
    }), 200

@chat_bp.route('/conversations/<int:conversation_id>/messages/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(conversation_id, message_id):
    """Delete a specific message."""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    message = Message.query.filter_by(
        id=message_id,
        conversation_id=conversation_id
    ).first()
    
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'message': 'Message deleted successfully'}), 200
