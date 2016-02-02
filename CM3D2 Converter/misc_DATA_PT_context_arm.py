import os, re, sys, bpy, time, bmesh, mathutils
from . import common

# メニュー等に項目追加
def menu_func(self, context):
	import re
	ob = context.active_object
	if not ob: return
	if ob.type != 'ARMATURE': return
	
	arm = ob.data
	is_boxed = False
	
	bone_data_count = 0
	if 'BoneData:0' in arm and 'LocalBoneData:0' in arm:
		for key in arm.keys():
			if re.search(r'^(Local)?BoneData:\d+$', key):
				bone_data_count += 1
	enabled_clipboard = False
	clipboard = context.window_manager.clipboard
	if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
		enabled_clipboard = True
	if bone_data_count or enabled_clipboard:
		if not is_boxed:
			box = self.layout.box()
			box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			is_boxed = True
		
		col = box.column(align=True)
		row = col.row(align=True)
		row.label(text="ボーン情報", icon='CONSTRAINT_BONE')
		sub_row = row.row()
		sub_row.alignment = 'RIGHT'
		if bone_data_count:
			sub_row.label(text=str(bone_data_count), icon='CHECKBOX_HLT')
		else:
			sub_row.label(text="0", icon='CHECKBOX_DEHLT')
		row = col.row(align=True)
		row.operator('object.copy_armature_bone_data_property', icon='COPYDOWN', text="コピー")
		row.operator('object.paste_armature_bone_data_property', icon='PASTEDOWN', text="貼り付け")
		row.operator('object.remove_armature_bone_data_property', icon='X', text="")
	
	flag = False
	for bone in arm.bones:
		if not flag and re.search(r'[_ ]([rRlL])[_ ]', bone.name):
			flag = True
		if not flag and bone.name.count('*') == 1:
			if re.search(r'\.([rRlL])$', bone.name):
				flag = True
		if flag:
			if not is_boxed:
				box = self.layout.box()
				box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
				is_boxed = True
			
			col = box.column(align=True)
			col.label(text="ボーン名変換", icon='SORTALPHA')
			row = col.row(align=True)
			row.operator('armature.decode_cm3d2_bone_names', text="CM3D2 → Blender", icon='BLENDER')
			row.operator('armature.encode_cm3d2_bone_names', text="Blender → CM3D2", icon_value=common.preview_collections['main']['KISS'].icon_id)
			break
	
	if 'is T Stance' in arm:
		if not is_boxed:
			box = self.layout.box()
			box.label(text="CM3D2用", icon_value=common.preview_collections['main']['KISS'].icon_id)
			is_boxed = True
		
		col = box.column(align=True)
		col.label(text="ポーズ", icon='POSE_HLT')
		row = col.row(align=True)
		
		sub_row = row.row(align=True)
		op = sub_row.operator('wm.context_set_int', icon='ARMATURE_DATA', text="オリジナル")
		op.data_path, op.value = 'scene.frame_current', 1
		if context.scene.frame_current % 2:
			sub_row.enabled = False
		
		sub_row = row.row(align=True)
		op = sub_row.operator('wm.context_set_int', icon='POSE_DATA', text="ポージング")
		op.data_path, op.value = 'scene.frame_current', 0
		if not context.scene.frame_current % 2:
			sub_row.enabled = False

class decode_cm3d2_bone_names(bpy.types.Operator):
	bl_idname = 'armature.decode_cm3d2_bone_names'
	bl_label = "ボーン名をCM3D2用→Blender用に変換"
	bl_description = "CM3D2で使われてるボーン名をBlenderで左右対称編集できるように変換します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		import re
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				for bone in arm.bones:
					if re.search(r'[_ ]([rRlL])[_ ]', bone.name):
						return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		arm = ob.data
		convert_count = 0
		for bone in arm.bones:
			bone_name = common.decode_bone_name(bone.name)
			if bone_name != bone.name:
				bone.name = bone_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="ボーン名をBlender用に変換しました")
		return {'FINISHED'}

class encode_cm3d2_bone_names(bpy.types.Operator):
	bl_idname = 'armature.encode_cm3d2_bone_names'
	bl_label = "ボーン名をBlender用→CM3D2用に変換"
	bl_description = "CM3D2で使われてるボーン名に元に戻します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		import re
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				for bone in arm.bones:
					if bone.name.count('*') == 1 and re.search(r'\.([rRlL])$', bone.name):
						return True
		return False
	
	def execute(self, context):
		ob = context.active_object
		arm = ob.data
		convert_count = 0
		for bone in arm.bones:
			bone_name = common.encode_bone_name(bone.name)
			if bone_name != bone.name:
				bone.name = bone_name
				convert_count += 1
		if convert_count == 0:
			self.report(type={'WARNING'}, message="変換できる名前が見つかりませんでした")
		else:
			self.report(type={'INFO'}, message="ボーン名をCM3D2用に戻しました")
		return {'FINISHED'}

class copy_armature_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.copy_armature_bone_data_property'
	bl_label = "ボーン情報をコピー"
	bl_description = "カスタムプロパティのボーン情報をクリップボードにコピーします"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				if 'BoneData:0' in arm and 'LocalBoneData:0' in arm:
					return True
		return False
	
	def execute(self, context):
		output_text = ""
		ob = context.active_object.data
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

class paste_armature_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.paste_armature_bone_data_property'
	bl_label = "ボーン情報を貼り付け"
	bl_description = "カスタムプロパティのボーン情報をクリップボードから貼り付けます"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				clipboard = context.window_manager.clipboard
				if 'BoneData:' in clipboard and 'LocalBoneData:' in clipboard:
					return True
		return False
	
	def execute(self, context):
		import re
		ob = context.active_object.data
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

class remove_armature_bone_data_property(bpy.types.Operator):
	bl_idname = 'object.remove_armature_bone_data_property'
	bl_label = "ボーン情報を削除"
	bl_description = "カスタムプロパティのボーン情報を全て削除します"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		ob = context.active_object
		if ob:
			if ob.type == 'ARMATURE':
				arm = ob.data
				if 'BoneData:0' in arm and 'LocalBoneData:0' in arm:
					return True
		return False
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		self.layout.label(text="カスタムプロパティのボーン情報を全て削除します", icon='CANCEL')
	
	def execute(self, context):
		ob = context.active_object.data
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
