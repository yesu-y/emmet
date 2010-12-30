#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Core Zen Coding library. Contains various text manipulation functions:

== Expand abbreviation
Expands abbreviation like ul#nav>li*5>a into a XHTML string.
=== How to use
First, you have to extract current string (where cursor is) from your test 
editor and use <code>find_abbr_in_line()</code> method to extract abbreviation. 
If abbreviation was found, this method will return it as well as position index
of abbreviation inside current line. If abbreviation wasn't 
found, method returns empty string. With abbreviation found, you should call
<code>parse_into_tree()</code> method to transform abbreviation into a tag tree. 
This method returns <code>Tag</code> object on success, None on failure. Then
simply call <code>to_string()</code> method of returned <code>Tag</code> object
to transoform tree into a XHTML string

You can setup output profile using <code>setup_profile()</code> method 
(see <code>default_profile</code> definition for available options) 

 
Created on Apr 17, 2009

@author: Sergey Chikuyonok (http://chikuyonok.ru)
'''
from zen_settings import zen_settings
import re
import zen_resources 
import zen_parser
import copy

newline = '\n'
"Newline symbol"

caret_placeholder = '{%::zen-caret::%}'

re_tag = re.compile(r'<\/?[\w:\-]+(?:\s+[\w\-:]+(?:\s*=\s*(?:(?:"[^"]*")|(?:\'[^\']*\')|[^>\s]+))?)*\s*(\/?)>$')

profiles = {}
"Available output profiles"

default_profile = {
	'tag_case': 'leave',         # values are 'lower', 'upper'
	'attr_case': 'leave',        # values are 'lower', 'upper'
	'attr_quotes': 'double',     # values are 'single', 'double'
	
	'tag_nl': 'decide',          # each tag on new line, values are True, False, 'decide'
	
	'place_cursor': True,        # place cursor char — | (pipe) — in output
	
	'indent': True,              # indent tags
	
	'inline_break': 3,           # how many inline elements should be to force line break (set to 0 to disable)
	
	'self_closing_tag': 'xhtml', # use self-closing style for writing empty elements, e.g. <br /> or <br>. 
                                 # values are True, False, 'xhtml'
                                 
	'filters': ''                # Profile-level output filters, re-defines syntax filters
}

basic_filters = 'html';
"Filters that will be applied for unknown syntax"

max_tabstop = 0
"Maximum tabstop index for current session"

def char_at(text, pos):
	"""
	Returns character at specified index of text.
	If index if out of range, returns empty string
	"""
	return text[pos] if pos < len(text) else ''

def is_allowed_char(ch):
	"""
	Test if passed symbol is allowed in abbreviation
	@param ch: Symbol to test
	@type ch: str
	@return: bool
	"""
	return ch.isalnum() or ch in "#.>+*:$-_!@[]()|"

def split_by_lines(text, remove_empty=False):
	"""
	Split text into lines. Set <code>remove_empty</code> to true to filter out
	empty lines
	@param text: str
	@param remove_empty: bool
	@return list
	"""
	lines = text.splitlines()
	
	return remove_empty and [line for line in lines if line.strip()] or lines

def create_profile(options):
	"""
	Create profile by adding default values for passed optoin set
	@param options: Profile options
	@type options: dict
	"""
	for k, v in default_profile.items():
		options.setdefault(k, v)
	
	return options

def setup_profile(name, options = {}):
	"""
	@param name: Profile name
	@type name: str
	@param options: Profile options
	@type options: dict
	"""
	profiles[name.lower()] = create_profile(options);

def get_newline():
	"""
	Returns newline symbol which is used in editor. This function must be 
	redefined to return current editor's settings 
	@return: str
	"""
	return newline

def set_newline(char):
	"""
	Sets newline character used in Zen Coding
	"""
	global newline
	newline = char

def pad_string(text, pad):
	"""
	Indents string with space characters (whitespace or tab)
	@param text: Text to indent
	@type text: str
	@param pad: Indentation level (number) or indentation itself (string)
	@type pad: int, str
	@return: str
	"""
	pad_str = ''
	result = ''
	if isinstance(pad, basestring):
		pad_str = pad
	else:
		pad_str = get_indentation() * pad
		
	nl = get_newline()
	
	lines = split_by_lines(text)
	
	if lines:
		result += lines[0]
		for line in lines[1:]:
			result += nl + pad_str + line
			
	return result

def is_snippet(abbr, syntax = 'html'):
	"""
	Check is passed abbreviation is a snippet
	@return bool
	"""
	return get_snippet(syntax, abbr) and True or False

def is_ends_with_tag(text):
	"""
	Test is string ends with XHTML tag. This function used for testing if '<'
	symbol belogs to tag or abbreviation 
	@type text: str
	@return: bool
	"""
	return re_tag.search(text) != None
	
def replace_variables(text, vars=zen_settings['variables']):
	"""
	Replace variables like ${var} in string
	@param text: str
	@return: str
	"""
	return re.sub(r'\$\{([\w\-]+)\}', lambda m: m.group(1) in vars and vars[m.group(1)] or m.group(0), text)

def filter_node_name(name):
	"""
	Removes any unnecessary characters from node name
	@type name: str
	@return: str
	"""
	return re.sub(r'(.+)\!$', '\\1', name)

def get_abbreviation(syntax, abbr):
	"""
	Returns abbreviation value from data set
	@param syntax: Resource syntax (html, css, ...)
	@type syntax: str
	@param abbr: Abbreviation name
	@type abbr: str
	@return dict, None
	"""
	return zen_resources.get_abbreviation(syntax, abbr)

def get_snippet(syntax, snippet_name):
	"""
	Returns snippet value from data set
	@param syntax: Resource syntax (html, css, ...)
	@type syntax: str
	@param snippet_name: Snippet name
	@type snippet_name: str
	@return dict, None
	"""
	return zen_resources.get_snippet(syntax, snippet_name)

def get_variable(name):
	"""
	Returns variable value
	 @return: str
	"""
	return zen_resources.get_variable(name)

def set_variable(name, value):
	voc = zen_resources.get_vocabulary('user') or {}
	if 'varaibles' not in voc:
		voc['variables'] = {}
		
	voc['variables'][name] = value
	zen_resources.set_vocabulary(voc, 'user')

def get_indentation():
	"""
	Returns indentation string
	@return {String}
	"""
	return get_variable('indentation')

def rollout_tree(tree, parent=None):
	"""
	Roll outs basic Zen Coding tree into simplified, DOM-like tree.
	The simplified tree, for example, represents each multiplied element 
	as a separate element sets with its own content, if exists.
	 
	The simplified tree element contains some meta info (tag name, attributes, 
	etc.) as well as output strings, which are exactly what will be outputted
	after expanding abbreviation. This tree is used for <i>filtering</i>:
	you can apply filters that will alter output strings to get desired look
	of expanded abbreviation.
	 
	@type tree: Tag
	@param parent: ZenNode
	"""
	if not parent:
		parent = ZenNode(tree)
		
	how_many = 1
	tag_content = ''
	
	for child in tree.children:
		how_many = child.count
		
		if child.repeat_by_lines:
			# it's a repeating element
			tag_content = split_by_lines(child.get_paste_content(), True)
			how_many = max(len(tag_content), 1)
		else:
			tag_content = child.get_paste_content()
		
		for j in xrange(how_many):
			tag = ZenNode(child)
			parent.add_child(tag)
			tag.counter = j + 1
			
			if child.children:
				rollout_tree(child, tag)
				
			if tag_content:
				text = isinstance(tag_content, basestring) and tag_content or tag_content[j] or ''
				tag.paste_content(text.strip())
					
	return parent

def run_filters(tree, profile, filter_list):
	"""
	Runs filters on tree
	@type tree: ZenNode
	@param profile: str, object
	@param filter_list: str, list
	@return: ZenNode
	"""
	import filters
	
	profile = process_profile(profile)
		
	if isinstance(filter_list, basestring):
		filter_list = re.split(r'[\|,]', filter_list)
		
	for name in filter_list:
		name = name.strip()
		if name and name in filters.filter_map:
			tree = filters.filter_map[name](tree, profile)
			
	return tree

def transform_tree_node(node, syntax='html'):
	"""
	Transforms abbreviation into a primary internal tree. This tree should'n 
	be used ouside of this scope
	@param node: Parsed tree node
	@type node: zen_parser.TreeNode
	@param syntax: Document syntax (xsl, html, etc.)
	@type syntax: str
	@return: Tag
	"""
	syntax = syntax or 'html';
	if node.is_empty(): return None
	
	return is_snippet(node.name, syntax) and Snippet(node, syntax) or Tag(node, syntax)

def process_parsed_node(node, syntax, parent):
	"""
	Process single tree node: expand it and its children 
	@type node: zen_parser.TreeNode
	@type syntax: str
	@type parent: Tag
	"""
	t_node = transform_tree_node(node, syntax)
	parent.add_child(t_node)
		
	# set repeating element to the topmost node
	root = parent
	while root.parent:
		root = root.parent
	
	root.last = t_node;
	if t_node.repeat_by_lines:
		root.multiply_elem = t_node
		
	# process child groups
	for child in node.children:
		process_parsed_node(child, syntax, t_node)

def replace_expandos(node, syntax):
	"""
	Replaces expando nodes by its parsed content
	@type node: zen_parser.TreeNode
	@type syntax: str
	"""
	for i, n in enumerate(node.children):
		if not n.is_empty() and not n.is_text_node() and '+' in n.name:
			# it's expando
			a = get_abbreviation(syntax, n.name)
			if a:
				node.children[i] = zen_parser.parse(a.value)
		
		replace_expandos(node.children[i], syntax)

def preprocess_parsed_tree(tree, syntax):
	"""
	Replaces expandos and optimizes tree structure by removing empty nodes
	@type tree: zen_parser.TreeNode
	@type syntax: str
	"""
	replace_expandos(tree, syntax)
	return zen_parser.optimize_tree(tree)

def replace_unescaped_symbol(text, symbol, replace):
	"""
	Replaces unescaped symbols in <code>text</code>. For example, the '$' symbol
	will be replaced in 'item$count', but not in 'item\$count'.
	@param text: Original string
	@type text: str
	@param symbol: Symbol to replace
	@type symbol: st
	@param replace: Symbol replacement
	@type replace: str, function 
	@return: str
	"""
	i = 0
	il = len(text)
	sl = len(symbol)
	match_count = 0
		
	while i < il:
		if text[i] == '\\':
			# escaped symbol, skip next character
			i += sl + 1
		elif text[i:i + sl] == symbol:
			# have match
			cur_sl = sl
			match_count += 1
			new_value = replace
			if callable(new_value):
				replace_data = replace(text, symbol, i, match_count)
				if replace_data:
					cur_sl = len(replace_data[0])
					new_value = replace_data[1]
				else:
					new_value = False
			
			if new_value is False: # skip replacement
				i += 1
				continue
			
			text = text[0:i] + new_value + text[i + cur_sl:]
			# adjust indexes
			il = len(text)
			i += len(new_value)
		else:
			i += 1
	
	return text

def process_profile(profile):
	"""
	Processes profile argument, returning, if possible, profile object
	"""
	_profile = profile
	if isinstance(profile, basestring) and profile in profiles:
		_profile = profiles[profile]
	
	if not _profile:
		_profile = profiles['plain']
		
	return _profile

	
def run_action(name, *args, **kwargs):
	"""
	 Runs Zen Coding action. For list of available actions and their
	 arguments see zen_actions.py file.
	 @param name: Action name 
	 @type name: str 
	 @param args: Additional arguments. It may be array of arguments
	 or inline arguments. The first argument should be <code>zen_editor</code> instance
	 @type args: list
	 @example
	 zen_coding.run_actions('expand_abbreviation', zen_editor)
	 zen_coding.run_actions('wrap_with_abbreviation', zen_editor, 'div')  
	"""
	import zen_actions
	
	if hasattr(zen_actions, name):
		return getattr(zen_actions, name)(*args, **kwargs)

def expand_abbreviation(abbr, syntax='html', profile_name='plain'):
	"""
	Expands abbreviation into a XHTML tag string
	@type abbr: str
	@return: str
	"""
	tree_root = parse_into_tree(abbr, syntax);
	if tree_root:
		tree = rollout_tree(tree_root)
		apply_filters(tree, syntax, profile_name, tree_root.filters)
		return replace_variables(tree.to_string())
	
	return ''

def extract_abbreviation(text):
	"""
	Extracts abbreviations from text stream, starting from the end
	@type text: str
	@return: Abbreviation or empty string
	"""
	cur_offset = len(text)
	start_index = -1
	brace_count = 0
	text_count = 0
	
	while True:
		cur_offset -= 1
		if cur_offset < 0:
			# moved at string start
			start_index = 0
			break
		
		ch = text[cur_offset]
		
		if ch == ']':
			brace_count += 1
		elif ch == '[':
			brace_count -= 1
		elif ch == '}':
			text_count += 1
		elif ch == '{':
			text_count -= 1
		else:
			if brace_count or text_count:
				# respect all characters inside attribute sets
				continue
			if not is_allowed_char(ch) or (ch == '>' and is_ends_with_tag(text[0:cur_offset + 1])):
				# found stop symbol
				start_index = cur_offset + 1
				break
		
	return text[start_index:] if start_index != -1 else ''

def parse_into_tree(abbr, syntax='html'):
	"""
	Parses abbreviation into a node set
	@param abbr: Abbreviation to transform
	@type abbr: str
	@param syntax: Document type (xsl, html), a key of dictionary where to
	search abbreviation settings
	@type syntax: str
	@return: Tag
	"""
	# remove filters from abbreviation
	filter_list = []
	
	def filter_replace(m):
		filter_list.append(m.group(1))
		return ''
	
	re_filter = re.compile(r'\|([\w\|\-]+)$')
	abbr = re_filter.sub(filter_replace, abbr)
	
	# try to parse abbreviation
	try:
		abbr_tree = zen_parser.parse(abbr)
		tree_root = Tag(None, syntax)
		abbr_tree = preprocess_parsed_tree(abbr_tree, syntax)
	except zen_parser.ZenInvalidAbbreviation:
		return None
		
	# then recursively expand each group item
	for child in abbr_tree.children:
		process_parsed_node(child, syntax, tree_root)
	
	tree_root.filters = filter_list
	return tree_root

def is_inside_tag(html, cursor_pos):
	re_tag = re.compile(r'^<\/?\w[\w\:\-]*.*?>')
	
	# search left to find opening brace
	pos = cursor_pos
	while pos > -1:
		if html[pos] == '<': break
		pos -= 1
	
	
	if pos != -1:
		m = re_tag.match(html[pos:]);
		if m and cursor_pos > pos and cursor_pos < pos + len(m.group(0)):
			return True

	return False

def wrap_with_abbreviation(abbr, text, syntax='html', profile='plain'):
	"""
	Wraps passed text with abbreviation. Text will be placed inside last
	expanded element
	@param abbr: Abbreviation
	@type abbr: str
	
	@param text: Text to wrap
	@type text: str
	
	@param syntax: Document type (html, xml, etc.)
	@type syntax: str
	
	@param profile: Output profile's name.
	@type profile: str
	@return {String}
	"""
	tree_root = parse_into_tree(abbr, syntax)
	if tree_root:
		repeat_elem = tree_root.multiply_elem or tree_root.last
		repeat_elem.set_paste_content(text)
		repeat_elem.repeat_by_lines = bool(tree_root.multiply_elem)
		
		tree = rollout_tree(tree_root)
		apply_filters(tree, syntax, profile, tree_root.filters)
		return replace_variables(tree.to_string())
	
	return None

def get_caret_placeholder():
	"""
	Returns caret placeholder
	@return: str
	"""
	if callable(caret_placeholder):
		return caret_placeholder()
	else:
		return caret_placeholder

def set_caret_placeholder(value):
	"""
	Set caret placeholder: a string (like '|') or function.
	You may use a function as a placeholder generator. For example,
	TextMate uses ${0}, ${1}, ..., ${n} natively for quick Tab-switching
	between them.
	@param {String|Function}
	"""
	global caret_placeholder
	caret_placeholder = value

def apply_filters(tree, syntax, profile, additional_filters=None):
	"""
	Applies filters to tree according to syntax
	@param tree: Tag tree to apply filters to
	@type tree: ZenNode
	@param syntax: Syntax name ('html', 'css', etc.)
	@type syntax: str
	@param profile: Profile or profile's name
	@type profile: str, object
	@param additional_filters: List or pipe-separated string of additional filters to apply
	@type additional_filters: str, list 
	 
	@return: ZenNode
	"""
	profile = process_profile(profile)
	_filters = profile['filters']
	if not _filters:
		_filters = zen_resources.get_subset(syntax, 'filters') or basic_filters
		
	if additional_filters:
		if additional_filters:
			_filters += '|'
			if isinstance(additional_filters, basestring):
				_filters += additional_filters
			else:
				_filters += '|'.join(additional_filters)
		
	if not _filters:
		# looks like unknown syntax, apply basic filters
		_filters = basic_filters
		
	return run_filters(tree, profile, _filters)

def replace_counter(text, value):
	"""
	 Replaces '$' character in string assuming it might be escaped with '\'
	 @type text: str
	 @type value: str, int
	 @return: str
	"""
	symbol = '$'
	value = str(value)
	
	def replace_func(tx, symbol, pos, match_num):
		if char_at(tx, pos + 1) == '{' or char_at(tx, pos + 1).isdigit():
			# it's a variable, skip it
			return False
		
		# replace sequense of $ symbols with padded number  
		j = pos + 1
		if j < len(text):
			while tx[j] == '$' and char_at(tx, j + 1) != '{': j += 1
		
		return (tx[pos:j], value.zfill(j - pos))
	
	return replace_unescaped_symbol(text, symbol, replace_func)

def upgrade_tabstops(node):
	"""
	Upgrades tabstops in zen node in order to prevent naming conflicts
	@type node: ZenNode
	@param offset: Tab index offset
	@type offset: int
	@returns Maximum tabstop index in element
	"""
	max_num = [0]
	props = ('start', 'end', 'content')
	
	def _replace(m):
		num = int(m.group(1) or m.group(2))
		if num > max_num[0]: max_num[0] = num
		return re.sub(r'\d+', str(num + max_tabstop), m.group(0), 1)
	
	for prop in props:
		node.__setattr__(prop, re.sub(r'\$(\d+)|\$\{(\d+):[^\}]+\}', _replace, node.__getattribute__(prop)))
		
	globals()['max_tabstop'] += max_num[0] + 1
		
	return max_num[0]

def escape_text(text):
	"""
	Escapes special characters used in Zen Coding, like '$', '|', etc.
	Use this method before passing to actions like "Wrap with Abbreviation"
	to make sure that existing spacial characters won't be altered
	@type text: str
	@return: str
	"""
	return re.sub(r'([\$\|\\])', r'\\\1', text)

def unescape_text(text):
	"""
	Unescapes special characters used in Zen Coding, like '$', '|', etc.
	@type text: str
	@return: str
	"""
	return re.sub(r'\\(.)', r'\1', text)

def get_profile(name):
	"""
	Get profile by it's name. If profile wasn't found, returns 'plain' profile
	"""
	return profiles[name] if name in profiles else profiles['plain']

def get_image_size(stream):
	"""
	Gets image size from image byte stream.
	@author http://romeda.org/rePublish/
	@param stream: Image byte stream (use <code>zen_file.read()</code>)
	@type stream: str
	@return: dict with <code>width</code> and <code>height</code> properties
	""" 
	png_magic_num = "\211PNG\r\n\032\n"
	jpg_magic_num = "\377\330"
	gif_magic_num = "GIF8"
	pos = [0]
	
	def next_byte():
		char = char_at(stream, pos[0])
		pos[0] += 1
		return ord(char)

	if stream.startswith(png_magic_num):
		# PNG. Easy peasy.
		pos[0] = stream.find('IHDR') + 4
	
		return {
			'width':  (next_byte() << 24) | (next_byte() << 16) | (next_byte() <<  8) | next_byte(),
			'height': (next_byte() << 24) | (next_byte() << 16) | (next_byte() <<  8) | next_byte()
		}
	
	elif stream.startswith(gif_magic_num):
		pos[0] = 6
	
		return {
			'width': next_byte() | (next_byte() << 8),
			'height': next_byte() | (next_byte() << 8)
		}
	
	elif stream.startswith(jpg_magic_num):
		hex_list = ["%02X" % ord(ch) for ch in stream]
		
		for k in range(len(hex_list) - 1):
			if hex_list[k] == 'FF' and (hex_list[k + 1] == 'C0' or hex_list[k + 1] == 'C2'):
				#print k, hex(k)  # test
				return {
					'height': int(hex_list[k + 5], 16) * 256 + int(hex_list[k + 6], 16),
					'width': int(hex_list[k + 7], 16) * 256 + int(hex_list[k + 8], 16)
				}
	else:
		return {
			'width': -1,
			'height': -1
		}

class Tag(object):
	def __init__(self, node, syntax='html'):
		"""
		@param node: Parsed tree node
		@type node: zen_parser.TreeNode
	 	@param syntax: Tag type (html, xml)
	 	@type syntax: str
		"""
		self.name = None
		self.real_name = None
		self.count = 1
		self.__abbr = None
		self.syntax = syntax
		self.__content = ''
		self.__paste_content = ''
		self.repeat_by_lines = False
		self.parent = None
		self.children = []
		self.attributes = []
		self.__attr_hash = {}
		
		if node:
			abbr = None
			if node.name:
				abbr = get_abbreviation(syntax, filter_node_name(node.name))
				if abbr and abbr.type == 'zen-reference':
					abbr = get_abbreviation(syntax, filter_node_name(abbr.value))
					
			self.name = abbr and abbr.value['name'] or node.name
			self.real_name = node.name
			self.count = node.count
			self.set_content(node.text)
			self.__abbr = abbr
			self.repeat_by_lines = node.is_repeating
		
		
		# add default attributes
		if self.__abbr:
			self.copy_attributes(self.__abbr.value)
		
		self.copy_attributes(node)
		
	def add_child(self, tag):
		"""
		Add new child
		@type tag: Tag
		"""
		tag.parent = self
		self.children.append(tag)
		
	def add_attribute(self, name, value):
		"""
		Add attribute to tag. If the attribute with the same name already exists,
		it will be overwritten, but if it's name is 'class', it will be merged
		with the existed one
		@param name: Attribute nama
		@type name: str
		@param value: Attribute value
		@type value: str
		"""
		
		# the only place in Tag where pipe (caret) character may exist
		# is the attribute: escape it with internal placeholder
		value = replace_unescaped_symbol(value, '|', get_caret_placeholder());
		
		if name in self.__attr_hash:
#			attribue already exists
			a = self.__attr_hash[name]
			if name == 'class':
#				'class' is a magic attribute
				if a['value']:
					value = ' ' + value
				a['value'] += value
			else:
				a['value'] = value
		else:
			a = {'name': name, 'value': value}
			self.__attr_hash[name] = a
			self.attributes.append(a)
			
	def copy_attributes(self, node):
		"""
		Copy attributes from parsed node
		"""
		attrs = None
		if node:
			if hasattr(node, 'attributes'):
				attrs = node.attributes
			elif 'attributes' in node:
				attrs = node['attributes']
			
		if attrs:
			for attr in attrs:
				self.add_attribute(attr['name'], attr['value'])
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains XHTML tags. 
	 	This function is mostly used for output formatting
		"""
		return self.get_content() and re_tag.search(self.get_content())
	
	def get_content(self):
		return self.__content
	
	def set_content(self, value):
		self.__content = replace_unescaped_symbol(value or '', '|', get_caret_placeholder())
		
	def set_paste_content(self, val):
		"""
		Set content that should be pasted to the output
		@type val: str
		"""
		self.__paste_content = escape_text(val)
	
	def get_paste_content(self):
		"""
		Get content that should be pasted to the output
		"""
		return self.__paste_content
	
		
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element.
		Returns None if there's no children
	 	@return Tag or None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
	def get_abbr(self):
		return self.__abbr
	
class Snippet(Tag):
	def __init__(self, node, syntax='html'):
		super(Snippet, self).__init__(node, syntax)
		self.attributes = {'id': get_caret_placeholder(), 'class': get_caret_placeholder()}
		self.value = replace_unescaped_symbol(get_snippet(syntax, self.name), '|', get_caret_placeholder())
	
	def is_block(self):
		return True
	
class ZenNode(object):
	"""
	Creates simplified tag from Zen Coding tag
	"""
	def __init__(self, tag):
		"""
		@type tag: Tag
		"""
		self.type = 'snippet' if isinstance(tag, Snippet) else 'tag'
		self.name = tag.name
		self.real_name = tag.real_name
		self.children = [];
		self.counter = 1
		
		# create deep copy of attribute list so we can change
		# their values in runtime without affecting other nodes
		# created from the same tag
		self.attributes = copy.deepcopy(tag.attributes)
		
		self.source = tag
		"Source element from which current tag was created"
		
		# relations
		self.parent = None
		self.next_sibling = None
		self.previous_sibling = None
		
		# output params
		self.start = ''
		self.end = ''
		self.content = tag.get_content() or ''
		self.padding = ''

	def add_child(self, tag):
		"""
		@type tag: ZenNode
		"""
		tag.parent = self
		
		if self.children:
			last_child = self.children[-1]
			tag.previous_sibling = last_child
			last_child.next_sibling = tag
		
		self.children.append(tag)
		
	def get_attribute(self, name):
		"""
		Get attribute's value.
		@type name: str
		@return: None if attribute wasn't found
		"""
		name = name.lower()
		for attr in self.attributes:
			if attr['name'].lower() == name:
				return attr['value']
		
		return None
	
	def is_unary(self):
		"""
		Test if current tag is unary (no closing tag)
		@return: bool
		"""
		if self.type == 'snippet':
			return False
			
		return self.source.get_abbr() and self.source.get_abbr().value['is_empty'] \
				or zen_resources.is_item_in_collection(self.source.syntax, 'empty', self.name)
	
	def is_inline(self):
		"""
		Test if current tag is inline-level (like <strong>, <img>)
		@return: bool
		"""
		return zen_resources.is_item_in_collection(self.source.syntax, 'inline_level', self.name)
	
	def is_block(self):
		"""
		Test if current element is block-level
		@return: bool
		"""
		return self.type == 'snippet' or not self.is_inline()
	
	def has_tags_in_content(self):
		"""
		This function tests if current tags' content contains xHTML tags. 
		This function is mostly used for output formatting
		"""
		return self.content and re_tag.search(self.content)
	
	def has_children(self):
		"""
		Check if tag has child elements
		@return: bool
		"""
		return bool(self.children)
	
	def has_block_children(self):
		"""
		Test if current tag contains block-level children
		@return: bool
		"""
		if self.has_tags_in_content() and self.is_block():
			return True
		
		for item in self.children:
			if item.is_block():
				return True
			
		return False
	
	def find_deepest_child(self):
		"""
		Search for deepest and latest child of current element
		Returns None if there's no children
		@return: ZenNode|None 
		"""
		if not self.children:
			return None
			
		deepest_child = self
		while True:
			deepest_child = deepest_child.children[-1]
			if not deepest_child.children:
				break
		
		return deepest_child
	
	def to_string(self):
		"@return {String}"
		content = ''.join([item.to_string() for item in self.children])
		return self.start + self.content + content + self.end
	
	def paste_content(self, text, had_var=0):
		"""
		Paste content in context of current node. Pasting is a special case
		of recursive adding content in node. 
		This function will try to find ${output} variable inside node's 
		attributes and text content and replace in with <code>text</code>.
		If it doesn't find ${output} variable, it will put <code>text</code>
		value as the deepest child content
		
		@param text: Test to paste
		@type text: str
		@param had_var: Flag indicating that previous function run
		(basically, on node's parent) had replaced ${output} variable (1),
		pasted as node content (2) or did nothing (0)
		@type had_var: int
		@return: Is text was pasted as ${output} variable (int)
		"""
		_had_var = [had_var]
		def fn(s, p1):
			if p1 == 'output':
				_had_var[0] = 1
				return text
			
			return s
		
		for a in self.attributes:
			a.value = replace_variables(a.value, fn)
			
		self.content = replace_variables(self.content, fn)
		if self.has_children():
			for child in self.children:
				_had_var[0] = child.paste_content(text, _had_var[0])
				if _had_var[0] == 2: return _had_var[0]
		elif _had_var[0] == 0:
			# put text as node content
			self.content += text
			return 2
		
		return _had_var[0]
		
class ZenError(Exception):
	"""
	Zen Coding specific error
	@since: 0.65
	"""
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)
		
# create default profiles
setup_profile('xhtml');
setup_profile('html', {'self_closing_tag': False});
setup_profile('xml', {'self_closing_tag': True, 'tag_nl': True});
setup_profile('plain', {'tag_nl': False, 'indent': False, 'place_cursor': False});
