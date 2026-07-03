from app.models.ModuleDTO import ModuleDTO


def build_modules_map(modules: list[ModuleDTO]) -> dict[str, ModuleDTO]:
    """
    Builds a module map indexed by module id

    Args:
        modules: Module DTOs

    Returns:
        Module map by id
    """
    out = {}

    for module in modules:
        module_id = module.get("id")
        if module_id is None:
            continue
        out[str(module_id)] = module

    return out
