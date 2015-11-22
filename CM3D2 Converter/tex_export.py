import os, re, bpy, struct, os.path, shutil
from . import common

class export_cm3d2_tex(bpy.types.Operator):
	bl_idname = "image.export_cm3d2_tex"
	bl_label = "texファイルを保存"
	bl_description = "CM3D2で使用されるテクスチャファイル(.tex)として保存します"
	bl_options = {'REGISTER'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".tex"
	filter_glob = bpy.props.StringProperty(default="*.tex", options={'HIDDEN'})
	
	is_backup = bpy.props.BoolProperty(name="ファイルをバックアップ", default=True, description="ファイルに上書きする場合にバックアップファイルを複製します")
	
	version = bpy.props.IntProperty(name="ファイルバージョン", default=1000, min=1000, max=1111, soft_min=1000, soft_max=1111, step=1)
	path = bpy.props.StringProperty(name="パス", default="assets/texture/texture/*.png")
	
	@classmethod
	def poll(cls, context):
		img = context.edit_image
		if img:
			if len(img.pixels):
				return True
		return False
	
	def invoke(self, context, event):
		img = context.edit_image
		if img.filepath:
			self.filepath = img.filepath
		else:
			if not context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_export_path:
				try:
					import winreg
					with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
						path = winreg.QueryValueEx(key, 'InstallPath')[0]
						path = os.path.join(path, 'GameData', '*.tex')
						context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_export_path = path
				except:
					pass
			head, tail = os.path.split(context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_export_path)
			self.filepath = os.path.join(head, common.remove_serial_number(img.name))
		root, ext = os.path.splitext(self.filepath)
		self.filepath = root + ".tex"
		self.is_backup = bool(context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext)
		self.path = "assets/texture/texture/" + os.path.basename(self.filepath)
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		row = self.layout.row()
		row.prop(self, 'is_backup', icon='FILE_BACKUP')
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
			row.enabled = False
		self.layout.prop(self, 'version', icon='LINENUMBERS_ON')
		self.layout.prop(self, 'path', icon='ANIM')
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.tex_export_path = self.filepath
		
		# バックアップ
		if self.is_backup and context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext:
			if os.path.exists(self.filepath):
				backup_path = self.filepath + "." + context.user_preferences.addons[__name__.split('.')[0]].preferences.backup_ext
				shutil.copyfile(self.filepath, backup_path)
				self.report(type={'INFO'}, message="上書き時にバックアップを複製しました")
		
		temp_path = self.filepath + ".temp.png"
		
		# とりあえずpngで保存
		img = context.edit_image
		pre_filepath = img.filepath
		pre_source = img.source
		bpy.ops.image.save_as(save_as_render=False, filepath=temp_path, relative_path=True, show_multiview=False, use_multiview=False)
		img.filepath = pre_filepath
		img.source = pre_source
		
		# pngバイナリを全て読み込み
		temp_file = open(temp_path, 'rb')
		temp_data = temp_file.read()
		temp_file.close()
		# 一時ファイルを削除
		os.remove(temp_path)
		
		# 本命ファイルに書き込み
		file = open(self.filepath, 'wb')
		common.write_str(file, 'CM3D2_TEX')
		file.write(struct.pack('<i', self.version))
		common.write_str(file, self.path)
		file.write(struct.pack('<i', len(temp_data)))
		file.write(temp_data)
		file.close()
		
		return {'FINISHED'}

# メニューを登録する関数
def menu_func(self, context):
	self.layout.operator(export_cm3d2_tex.bl_idname, icon_value=common.preview_collections['main']['KISS'].icon_id)
