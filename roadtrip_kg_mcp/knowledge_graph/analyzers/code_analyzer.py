"""
AST-based code analyzer for building the knowledge graph
"""
import ast
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import hashlib
from pathlib import Path


@dataclass
class CodeEntity:
    """Represents a code entity found during analysis"""
    id: str
    type: str  # module, class, function, method, variable
    name: str
    path: str
    line_start: int
    line_end: int
    content: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PythonCodeAnalyzer(ast.NodeVisitor):
    """Analyze Python code and extract entities and relationships"""
    
    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.split('\n')
        self.entities: List[CodeEntity] = []
        self.relationships: List[Tuple[str, str, str]] = []  # (source, target, type)
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self.import_map: Dict[str, str] = {}  # alias -> full name
        
        # Generate file entity
        self.file_id = self._generate_id("file", file_path)
        self.entities.append(CodeEntity(
            id=self.file_id,
            type="file",
            name=os.path.basename(file_path),
            path=file_path,
            line_start=1,
            line_end=len(self.lines),
            content=content,
            metadata={"extension": Path(file_path).suffix}
        ))
    
    def analyze(self) -> Tuple[List[CodeEntity], List[Tuple[str, str, str]]]:
        """Analyze the code and return entities and relationships"""
        try:
            tree = ast.parse(self.content, filename=self.file_path)
            self.visit(tree)
        except SyntaxError as e:
            print(f"Syntax error in {self.file_path}: {e}")
        
        return self.entities, self.relationships
    
    def visit_Import(self, node: ast.Import):
        """Handle import statements"""
        for alias in node.names:
            import_name = alias.name
            import_alias = alias.asname or alias.name
            self.import_map[import_alias] = import_name
            
            # Add import relationship
            self.relationships.append((self.file_id, import_name, "imports"))
            
            # Add to current context
            if self.current_function:
                for entity in self.entities:
                    if entity.id == self.current_function:
                        entity.imports.append(import_name)
                        break
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handle from ... import statements"""
        module = node.module or ''
        for alias in node.names:
            import_name = f"{module}.{alias.name}"
            import_alias = alias.asname or alias.name
            self.import_map[import_alias] = import_name
            
            # Add import relationship
            self.relationships.append((self.file_id, import_name, "imports"))
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Handle class definitions"""
        class_id = self._generate_id("class", f"{self.file_path}:{node.name}")
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}")
        
        entity = CodeEntity(
            id=class_id,
            type="class",
            name=node.name,
            path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            content=self._get_node_content(node),
            docstring=docstring,
            decorators=decorators,
            parent_id=self.file_id,
            metadata={"bases": bases}
        )
        
        self.entities.append(entity)
        self.relationships.append((class_id, self.file_id, "defined_in"))
        
        # Add inheritance relationships
        for base in bases:
            self.relationships.append((class_id, base, "extends"))
        
        # Visit class body
        old_class = self.current_class
        self.current_class = class_id
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Handle function definitions"""
        self._visit_function(node, "function")
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Handle async function definitions"""
        self._visit_function(node, "async_function")
    
    def _visit_function(self, node, func_type: str):
        """Handle function/method definitions"""
        parent_id = self.current_class or self.file_id
        func_name = node.name
        
        if self.current_class:
            func_type = "method"
            func_id = self._generate_id(func_type, f"{self.file_path}:{self.current_class}:{func_name}")
        else:
            func_id = self._generate_id(func_type, f"{self.file_path}:{func_name}")
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        # Extract parameters
        params = []
        for arg in node.args.args:
            params.append(arg.arg)
        
        entity = CodeEntity(
            id=func_id,
            type=func_type,
            name=func_name,
            path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            content=self._get_node_content(node),
            docstring=docstring,
            decorators=decorators,
            parent_id=parent_id,
            metadata={
                "parameters": params,
                "is_async": isinstance(node, ast.AsyncFunctionDef)
            }
        )
        
        self.entities.append(entity)
        self.relationships.append((func_id, parent_id, "defined_in"))
        
        # Visit function body
        old_function = self.current_function
        self.current_function = func_id
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Call(self, node: ast.Call):
        """Handle function calls"""
        if self.current_function:
            call_name = self._get_call_name(node)
            if call_name:
                # Add to current function's calls
                for entity in self.entities:
                    if entity.id == self.current_function:
                        entity.calls.append(call_name)
                        break
                
                # Add call relationship
                self.relationships.append((self.current_function, call_name, "calls"))
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the name of a function call"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
        return None
    
    def _get_decorator_name(self, node) -> str:
        """Extract decorator name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_call_name(node) or "unknown"
        return "unknown"
    
    def _get_node_content(self, node) -> str:
        """Get the source code for a node"""
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            start = node.lineno - 1
            end = node.end_lineno
            return '\n'.join(self.lines[start:end])
        return ""
    
    def _generate_id(self, entity_type: str, unique_name: str) -> str:
        """Generate a unique ID for an entity"""
        return hashlib.sha256(f"{entity_type}:{unique_name}".encode()).hexdigest()[:16]


class CodebaseAnalyzer:
    """Analyze entire codebase"""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.entities: List[CodeEntity] = []
        self.relationships: List[Tuple[str, str, str]] = []
        self.file_map: Dict[str, str] = {}  # file_path -> file_id
    
    def analyze_codebase(self, extensions: List[str] = ['.py']) -> Tuple[List[CodeEntity], List[Tuple[str, str, str]]]:
        """Analyze all files in the codebase"""
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    self._analyze_file(file_path)
        
        # Post-process to resolve cross-file relationships
        self._resolve_cross_file_relationships()
        
        return self.entities, self.relationships
    
    def _analyze_file(self, file_path: str):
        """Analyze a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analyzer = PythonCodeAnalyzer(file_path, content)
            file_entities, file_relationships = analyzer.analyze()
            
            self.entities.extend(file_entities)
            self.relationships.extend(file_relationships)
            
            # Store file mapping
            for entity in file_entities:
                if entity.type == "file":
                    self.file_map[file_path] = entity.id
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _resolve_cross_file_relationships(self):
        """Resolve relationships across files"""
        # Build a map of all defined entities
        entity_map = {}
        for entity in self.entities:
            if entity.type in ["class", "function"]:
                entity_map[entity.name] = entity.id
                
                # Also map with module prefix
                module_name = Path(entity.path).stem
                entity_map[f"{module_name}.{entity.name}"] = entity.id
        
        # Update relationships with resolved IDs
        resolved_relationships = []
        for source, target, rel_type in self.relationships:
            # Try to resolve target if it's a string name
            if rel_type in ["calls", "extends", "imports"]:
                if target in entity_map:
                    target = entity_map[target]
            
            resolved_relationships.append((source, target, rel_type))
        
        self.relationships = resolved_relationships