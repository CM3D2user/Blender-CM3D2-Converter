import os, re, bpy, struct, os.path, shutil

def ReadStr(file):
	str_index = struct.unpack('<B', file.read(1))[0]
	if 128 <= str_index:
		i = struct.unpack('<B', file.read(1))[0]
		str_index += (i * 128) - 128
	try:
		return file.read(str_index).decode('utf-8')
	except:
		pass
	return None

class import_cm3d2_mate_text(bpy.types.Operator):
	bl_idname = 'text.import_cm3d2_mate_text'
	bl_label = "mateを開く"
	bl_description = "mateファイルをテキストとして開きます"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath = bpy.props.StringProperty(subtype='FILE_PATH')
	filename_ext = ".mate"
	filter_glob = bpy.props.StringProperty(default="*.mate", options={'HIDDEN'})
	
	is_overwrite = bpy.props.BoolProperty(name="現在のテキストに上書き", default=False)
	
	@classmethod
	def poll(cls, context):
		return True
	
	def invoke(self, context, event):
		if not context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_import_path:
			try:
				import winreg
				with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\KISS\カスタムメイド3D2') as key:
					path = winreg.QueryValueEx(key, 'InstallPath')[0]
					path = os.path.join(path, 'GameData', '*.mate')
					context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_import_path = path
			except:
				pass
		self.filepath = context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_import_path
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}
	
	def draw(self, context):
		self.layout.prop(self, 'is_overwrite', icon='SAVE_COPY')
	
	def execute(self, context):
		context.user_preferences.addons[__name__.split('.')[0]].preferences.mate_import_path = self.filepath
		
		if self.is_overwrite:
			if 'edit_text' not in dir(context):
				self.report(type={'ERROR'}, message="上書きする為のテキストデータが見つかりません")
				return {'CANCELLED'}
			if not context.edit_text:
				self.report(type={'ERROR'}, message="上書きする為のテキストデータが見つかりません")
				return {'CANCELLED'}
			txt = context.edit_text
			txt.clear()
		else:
			txt = context.blend_data.texts.new(os.path.basename(self.filepath))
			context.area.type = 'TEXT_EDITOR'
			context.space_data.text = txt
		
		file = open(self.filepath, 'rb')
		if ReadStr(file) != 'CM3D2_MATERIAL':
			self.report(type={'ERROR'}, message="これはmateファイルではありません、中止します")
			return {'CANCELLED'}
		txt.write( str(struct.unpack('<i', file.read(4))[0]) + "\n" )
		txt.write( ReadStr(file) + "\n" )
		txt.write( ReadStr(file) + "\n" )
		txt.write( ReadStr(file) + "\n" )
		txt.write( ReadStr(file) + "\n" )
		txt.write("\n")
		
		for i in range(99999):
			type = ReadStr(file)
			if type == 'tex':
				txt.write( type + "\n" )
				txt.write( "\t" + ReadStr(file) + "\n" )
				tex_type = ReadStr(file)
				txt.write( "\t" + tex_type + "\n" )
				if tex_type == 'tex2d':
					txt.write( "\t" + ReadStr(file) + "\n" )
					txt.write( "\t" + ReadStr(file) + "\n" )
					fs = struct.unpack('<4f', file.read(4*4))
					txt.write( "\t" + str(fs[0]) + " " + str(fs[1]) + " " + str(fs[2]) + " " + str(fs[3]) + "\n" )
			elif type == 'col':
				txt.write( type + "\n" )
				txt.write( "\t" + ReadStr(file) + "\n" )
				fs = struct.unpack('<4f', file.read(4*4))
				txt.write( "\t" + str(fs[0]) + " " + str(fs[1]) + " " + str(fs[2]) + " " + str(fs[3]) + "\n" )
			elif type == 'f':
				txt.write( type + "\n" )
				txt.write( "\t" + ReadStr(file) + "\n" )
				txt.write( "\t" + str(struct.unpack('<f', file.read(4))[0]) + "\n" )
			elif type == 'end':
				break
			else:
				self.report(type={'ERROR'}, message="未知の設定値タイプが見つかりました、中止します")
				return {'CANCELLED'}
		
		file.close()
		txt.current_line_index = 0
		return {'FINISHED'}

# テキストメニューに項目を登録
def TEXT_MT_text(self, context):
	self.layout.separator()
	self.layout.operator(import_cm3d2_mate_text.bl_idname, icon_value=context.user_preferences.addons[__name__.split('.')[0]].preferences.kiss_icon_value)
