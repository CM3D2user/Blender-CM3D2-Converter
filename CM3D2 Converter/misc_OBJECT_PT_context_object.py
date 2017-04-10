# 「プロパティ」エリア → 「オブジェクト」タブ
import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	import re
	ob = context.active_object
	if not ob: return
	if ob.type != 'MESH': return
	
	bone_data_count = 0
	if 'BoneData:0' in ob and 'LocalBoneData:0' in ob:
		for key in ob.keys():
			if re.search(r'^(Local)?BoneData:\d+$', key):
				bone_data_count += 1
	enabled_clipboard = False
	clipboard = context.window_manager.clipboard
	if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
		enabled_clipboard = True
	
	if bone_data_count or enabled_clipboard:
		col = self.layout.column(align=True)
		row = col.row(align=True)
		row.label(text="CM3D2用ボーン情報", icon_value=common.preview_collections['main']['KISS'].icon_id)
		sub_row = row.row()
		sub_row.alignment = 'RIGHT'
		if 'BoneData:0' in ob and 'LocalBoneData:0' in ob:
			bone_data_count = 0
			for key in ob.keys():
				if re.search(r'^(Local)?BoneData:\d+$', key):
					bone_data_count += 1
			sub_row.label(text=str(bone_data_count), icon='CHECKBOX_HLT')
		else:
			sub_row.label(text="0", icon='CHECKBOX_DEHLT')
		row = col.row(align=True)
		row.operator('object.copy_object_bone_data_property', icon='COPYDOWN', text="コピー")
		row.operator('object.paste_object_bone_data_property', icon='PASTEDOWN', text="貼り付け")
		row.operator('object.remove_object_bone_data_property', icon='X', text="")

class copy_object_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.copy_object_bone_data_property'
	bl_label = "ボーン情報をコピー"
	bl_description = "カスタムプロパティのボーン情報をクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if 'BoneData:0' in ob and 'LocalBoneData:0' in ob:
				return True
		return False
	
	def execute(self, context):
		output_text = ""
		ob = context.active_object
		pass_count = 0
		if 'BaseBone' in ob:
			output_text += "BaseBone:" + ob['BaseBone'] + "\n"
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob:
				output_text += "BoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob:
				output_text += "LocalBoneData:" + ob[name] + "\n"
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		context.window_manager.clipboard = output_text
		self.report(type={'INFO'}, message="ボーン情報をクリップボードにコピーしました")
		return {'FINISHED'}

class paste_object_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.paste_object_bone_data_property'
	bl_label = "ボーン情報を貼り付け"
	bl_description = "カスタムプロパティのボーン情報をクリップボードから貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			clipboard = context.window_manager.clipboard
			if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
				return True
		return False
	
	def execute(self, context):
		import re
		ob = context.active_object
		pass_count = 0
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob:
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob:
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		bone_data_count = 0
		local_bone_data_count = 0
		for line in context.window_manager.clipboard.split("\n"):
			r = re.search('^BaseBone:(.+)$', line)
			if r:
				ob['BaseBone'] = r.groups()[0]
			r = re.search('^BoneData:(.+)$', line)
			if r:
				if line.count(',') == 4:
					info = r.groups()[0]
					name = "BoneData:" + str(bone_data_count)
					ob[name] = info
					bone_data_count += 1
			r = re.search('^LocalBoneData:(.+)$', line)
			if r:
				if line.count(',') == 1:
					info = r.groups()[0]
					name = "LocalBoneData:" + str(local_bone_data_count)
					ob[name] = info
					local_bone_data_count += 1
		self.report(type={'INFO'}, message="ボーン情報をクリップボードから貼り付けました")
		return {'FINISHED'}

class remove_object_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.remove_object_bone_data_property'
	bl_label = "ボーン情報を削除"
	bl_description = "カスタムプロパティのボーン情報を全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if 'BoneData:0' in ob and 'LocalBoneData:0' in ob:
				return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="カスタムプロパティのボーン情報を全て削除します", icon='CANCEL')
	
	def execute(self, context):
		ob = context.active_object
		pass_count = 0
		if 'BaseBone' in ob:
			del ob['BaseBone']
		for i in range(99999):
			name = "BoneData:" + str(i)
			if name in ob:
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		pass_count = 0
		for i in range(99999):
			name = "LocalBoneData:" + str(i)
			if name in ob:
				del ob[name]
			else:
				pass_count += 1
			if 10 < pass_count:
				break
		self.report(type={'INFO'}, message="ボーン情報を削除しました")
		return {'FINISHED'}
