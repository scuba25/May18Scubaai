from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from marshmallow import Schema, fields, ValidationError

from models import db, CustomInstruction, SystemSetting
from services.settings_service import SettingsService

settings_bp = Blueprint('settings', __name__)

# Schemas for request validation
class CustomInstructionSchema(Schema):
    name = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    content = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    is_default = fields.Bool(default=False)

class SystemSettingSchema(Schema):
    key = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    value = fields.Str(required=True)
    description = fields.Str(required=False, allow_none=True)

custom_instruction_schema = CustomInstructionSchema()
system_setting_schema = SystemSettingSchema()

# Custom Instructions endpoints
@settings_bp.route('/instructions', methods=['GET'])
@jwt_required()
def get_custom_instructions():
    """Get all custom instructions for the current user."""
    instructions = CustomInstruction.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'custom_instructions': [instr.to_dict() for instr in instructions]
    }), 200

@settings_bp.route('/instructions', methods=['POST'])
@jwt_required()
def create_custom_instruction():
    """Create a new custom instruction."""
    try:
        data = custom_instruction_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    # Check if we're setting this as default
    if data.get('is_default'):
        # Unset any existing default instruction for this user
        SettingsService.unset_default_instruction(current_user.id)
    
    instruction = CustomInstruction(
        user_id=current_user.id,
        name=data['name'].strip(),
        content=data['content'].strip(),
        is_default=data.get('is_default', False)
    )
    
    db.session.add(instruction)
    db.session.commit()
    
    return jsonify({
        'message': 'Custom instruction created successfully',
        'custom_instruction': instruction.to_dict()
    }), 201

@settings_bp.route('/instructions/<int:instruction_id>', methods=['GET'])
@jwt_required()
def get_custom_instruction(instruction_id):
    """Get a specific custom instruction."""
    instruction = CustomInstruction.query.filter_by(
        id=instruction_id,
        user_id=current_user.id
    ).first()
    
    if not instruction:
        return jsonify({'error': 'Custom instruction not found'}), 404
    
    return jsonify({
        'custom_instruction': instruction.to_dict()
    }), 200

@settings_bp.route('/instructions/<int:instruction_id>', methods=['PUT'])
@jwt_required()
def update_custom_instruction(instruction_id):
    """Update a custom instruction."""
    try:
        data = custom_instruction_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    instruction = CustomInstruction.query.filter_by(
        id=instruction_id,
        user_id=current_user.id
    ).first()
    
    if not instruction:
        return jsonify({'error': 'Custom instruction not found'}), 404
    
    # Check if we're setting this as default
    if data.get('is_default') and not instruction.is_default:
        # Unset any existing default instruction for this user
        SettingsService.unset_default_instruction(current_user.id)
    
    instruction.name = data['name'].strip()
    instruction.content = data['content'].strip()
    instruction.is_default = data.get('is_default', instruction.is_default)
    instruction.updated_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Custom instruction updated successfully',
        'custom_instruction': instruction.to_dict()
    }), 200

@settings_bp.route('/instructions/<int:instruction_id>', methods=['DELETE'])
@jwt_required()
def delete_custom_instruction(instruction_id):
    """Delete a custom instruction."""
    instruction = CustomInstruction.query.filter_by(
        id=instruction_id,
        user_id=current_user.id
    ).first()
    
    if not instruction:
        return jsonify({'error': 'Custom instruction not found'}), 404
    
    db.session.delete(instruction)
    db.session.commit()
    
    return jsonify({'message': 'Custom instruction deleted successfully'}), 200

@settings_bp.route('/instructions/<int:instruction_id>/set-default', methods=['POST'])
@jwt_required()
def set_default_instruction(instruction_id):
    """Set a custom instruction as the default."""
    instruction = CustomInstruction.query.filter_by(
        id=instruction_id,
        user_id=current_user.id
    ).first()
    
    if not instruction:
        return jsonify({'error': 'Custom instruction not found'}), 404
    
    # Unset any existing default instruction
    SettingsService.unset_default_instruction(current_user.id)
    
    # Set this instruction as default
    instruction.is_default = True
    instruction.updated_at = db.func.now()
    db.session.commit()
    
    return jsonify({
        'message': 'Custom instruction set as default successfully',
        'custom_instruction': instruction.to_dict()
    }), 200

# System Settings endpoints (Admin only)
@settings_bp.route('/system', methods=['GET'])
@jwt_required()
def get_system_settings():
    """Get all system settings."""
    settings = SystemSetting.query.all()
    
    return jsonify({
        'system_settings': [setting.to_dict() for setting in settings]
    }), 200

@settings_bp.route('/system', methods=['POST'])
@jwt_required()
def create_system_setting():
    """Create a new system setting (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = system_setting_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    # Check if key already exists
    existing = SystemSetting.query.filter_by(key=data['key']).first()
    if existing:
        return jsonify({'error': 'System setting with this key already exists'}), 409
    
    setting = SystemSetting(
        key=data['key'].strip(),
        value=data['value'],
        description=data.get('description')
    )
    
    db.session.add(setting)
    db.session.commit()
    
    return jsonify({
        'message': 'System setting created successfully',
        'system_setting': setting.to_dict()
    }), 201

@settings_bp.route('/system/<int:setting_id>', methods=['PUT'])
@jwt_required()
def update_system_setting(setting_id):
    """Update a system setting (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = system_setting_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'Validation error', 'messages': err.messages}), 400
    
    setting = SystemSetting.query.get(setting_id)
    if not setting:
        return jsonify({'error': 'System setting not found'}), 404
    
    # Update fields
    setting.key = data['key'].strip()
    setting.value = data['value']
    setting.description = data.get('description', setting.description)
    setting.updated_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'System setting updated successfully',
        'system_setting': setting.to_dict()
    }), 200

@settings_bp.route('/system/<int:setting_id>', methods=['DELETE'])
@jwt_required()
def delete_system_setting(setting_id):
    """Delete a system setting (admin only)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    setting = SystemSetting.query.get(setting_id)
    if not setting:
        return jsonify({'error': 'System setting not found'}), 404
    
    db.session.delete(setting)
    db.session.commit()
    
    return jsonify({'message': 'System setting deleted successfully'}), 200

@settings_bp.route('/system/<string:key>', methods=['GET'])
@jwt_required()
def get_system_setting_by_key(key):
    """Get a system setting by key."""
    setting = SystemSetting.query.filter_by(key=key).first()
    if not setting:
        return jsonify({'error': 'System setting not found'}), 404
    
    return jsonify({'system_setting': setting.to_dict()}), 200

# User preferences endpoints
@settings_bp.route('/preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    """Get user preferences."""
    # You can expand this to include user-specific preferences
    # For now, we'll return the user's default custom instruction
    default_instruction = CustomInstruction.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()
    
    preferences = {
        'default_custom_instruction': default_instruction.to_dict() if default_instruction else None,
        'user': current_user.to_dict()
    }
    
    return jsonify({'preferences': preferences}), 200

@settings_bp.route('/export', methods=['GET'])
@jwt_required()
def export_user_data():
    """Export user data including conversations and custom instructions."""
    from models import Conversation, Message
    
    # Get user's conversations and messages
    conversations = Conversation.query.filter_by(user_id=current_user.id).all()
    custom_instructions = CustomInstruction.query.filter_by(user_id=current_user.id).all()
    
    export_data = {
        'user': current_user.to_dict(),
        'custom_instructions': [ci.to_dict() for ci in custom_instructions],
        'conversations': []
    }
    
    for conv in conversations:
        messages = Message.query.filter_by(conversation_id=conv.id)\
                              .order_by(Message.created_at.asc())\
                              .all()
        
        conv_data = conv.to_dict()
        conv_data['messages'] = [msg.to_dict() for msg in messages]
        export_data['conversations'].append(conv_data)
    
    return jsonify({
        'message': 'User data exported successfully',
        'data': export_data
    }), 200
