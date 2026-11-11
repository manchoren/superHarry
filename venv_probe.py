import home.model_interface
print("model_interface file:", home.model_interface.__file__)
import home.gemini_chat
print("gemini_chat file:", home.gemini_chat.__file__)
try:
    from home.model_interface import ContextProfile
    print("ContextProfile imported OK from", home.model_interface.__file__)
except ImportError as e:
    print("ImportError:", e)
import home.constitution_context
print("constitution_context file:", home.constitution_context.__file__)
print("ContextProfile defined in constitution_context:", hasattr(home.constitution_context, "ContextProfile"))
