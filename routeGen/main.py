#! /user/bin/env python3
# Script will take directory as arg --done
from pathlib import Path
import argparse
import os
import json
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_javascript
from collections import defaultdict
from routeGen.script import convert_file

#constants
JS_LANGUAGE = Language(tree_sitter_javascript.language())
Js_parser = Parser(JS_LANGUAGE)

#utils function
def is_dir_exist(path):
    p = Path(path)
    if not p.is_dir():
        raise argparse.ArgumentTypeError(f"{path} is not valid directory")
    return p

def read_file(path):
    with open(path,'r') as file:
        content = file.read()
        return content

def resolve_import_name(import_path,target_file_path):
    # write logic for changing path "./users/users.js" to /users/users.js
    # Strip quotes if Tree-sitter gives something like '"./user.js"'
    import_path = import_path.strip('"\'')   # removes " or '

    current_file = Path(target_file_path).resolve()

    # Only handle relative or absolute filesystem paths
    if not import_path.startswith(('.', '/')):
        return None

    # Absolute path
    if import_path.startswith('/'):
        abs_path = Path(import_path).resolve()
        return str(abs_path) if abs_path.exists() else None

    # Relative import: "./", "../"
    abs_path = (current_file.parent / import_path).resolve()

    return str(abs_path) if abs_path.exists() else None


def get_matches_from_jsfile(content,query_src):
    code = Js_parser.parse(bytes(content,'utf8'))
    root = code.root_node
    query = Query(JS_LANGUAGE,query_src)
    cursor = QueryCursor(query)
    matches = cursor.matches(root)
    return matches


#logical function
def get_func_handler_import_file(content,handler,target_file_path):
    #get more details from handler func
    query_src = """
    (
      import_statement
        (import_clause)? @imports
        (string) @path
    )
    """
    code_bytes = content.encode("utf8")
    matches = get_matches_from_jsfile(content,query_src)
    abs_import_name = None
    print(matches)
    for _,captures_dict in matches:
        if 'imports' not in captures_dict:
            continue
        import_node = captures_dict['imports'][0]
        path_node  = captures_dict['path'][0]

        import_name = code_bytes[import_node.start_byte:import_node.end_byte].decode()
        path_name = code_bytes[path_node.start_byte:path_node.end_byte].decode()
        if import_name != handler:
            # resolve import path name
            continue
        abs_import_name = resolve_import_name(path_name,target_file_path)
    return abs_import_name

def find_details_as_route_info(content,target_file_path):
    basic_route_info = {} 
    query_src = """
    (call_expression
      function: (member_expression
          object: (identifier) @object
          property: (property_identifier) @method)
      arguments: (arguments (string) @path (identifier) @handler))
    """
    matches = get_matches_from_jsfile(content,query_src)
    code_bytes = content.encode('utf8')
    path = None
    handler = None
    
    for _, captures_dict in matches:
        obj_node = captures_dict['object'][0]
        method_node = captures_dict['method'][0]
        path_node = captures_dict['path'][0]
        handler_node = captures_dict['handler'][0]
    
        # Get actual text
        obj = code_bytes[obj_node.start_byte:obj_node.end_byte].decode()
        method = code_bytes[method_node.start_byte:method_node.end_byte].decode()

        # Only app.use
        if obj != "app" and method != "use":
            continue

        path = code_bytes[path_node.start_byte:path_node.end_byte].decode().strip("'\"")
        handler = code_bytes[handler_node.start_byte:handler_node.end_byte].decode()
        handler_location_info = get_func_handler_import_file(content,handler,target_file_path)
        
        d = basic_route_info.setdefault(handler,{})
        d["path"] = path
        d["handler"] = handler
        d['handler_file_info'] = handler_location_info
    
    # find route func handler import file info
    return basic_route_info 


def get_hanlder_func_route_details(handler_location_info,route_info):
    # get handler function absolute path to get into that file
    # getting content of handler file
    query_src = """
    (
  call_expression
    function: (
      member_expression
        object: (identifier) @object
        property: (property_identifier) @method
    )
    arguments: (
      arguments
        (string) @path 
        (expression) @handlerFunc
    )
)
    """
    content = read_file(handler_location_info)
    matches = get_matches_from_jsfile(content,query_src)
    
    captures_dict = []
    for _,captures in matches:
        captures_dict.append(captures)

    route_data = defaultdict(list)
        
    for caps in captures_dict:
        obj = caps['object'][0].text.decode()
        method = caps['method'][0].text.decode()
        path = caps['path'][0].text.decode()
        key = (
            obj,
            method,
            path
        )
        route_data[key].extend([node.text.decode() for node in caps.get('handlerFunc',[])])

        # obj should be router, method will give details on http request type
        if obj != 'router':
            continue
        # print('next')

        # adding to dict
        for (obj,method,path) , handlers in route_data.items():
            route_info[path] = {
                "sub_path": path,
                "httpMethod": method,
                "handlerFunc": handlers
            }



#business function
def find_details_for_routes(content,target_file_path):
    # find path and it's handler for app.use('/',func) 
    basic_route_info = find_details_as_route_info(content,target_file_path)
    for name,route_info in basic_route_info.items():
        handler_location_info = route_info['handler_file_info']
        get_hanlder_func_route_details(handler_location_info,route_info)

    return basic_route_info
    # return handlerFunc , route , subsroutes, subroutes handlerfunc


def output(results):
    #write logic for converting it to md file
    json_data = json.dumps(results,indent=4)
    print(json_data)
    convert_file(results)

def main():
    # 1. Get Args as directory    
    parser = argparse.ArgumentParser()

    parser.add_argument("-d",required=True,type=is_dir_exist)
    args = parser.parse_args()

    dirName = args.d
    dirPath = dirName.resolve()
    index_file_path = ''

    for (roots,dirs,files) in os.walk(dirPath):
        if 'index.js' in files:
            index_file_path = os.path.join(roots,'index.js')
            break

    file_content = read_file(index_file_path)
    

    # 2. Getting Details
    route_info = find_details_for_routes(file_content,index_file_path)
    output(route_info)


    # 3. Show all info as output (JSON for now , later Md)    


if __name__ == '__main__':
    main()
        
