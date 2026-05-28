"""参考图管理器：目录 → 属性映射，IDE 自动补全。"""

from pathlib import Path


class ImageRef:
    """对参考图片文件的轻量引用，供匹配引擎使用。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __repr__(self) -> str:
        return f"ImageRef({self.path})"

    def __fspath__(self) -> str:
        return str(self.path)


class ImageDirMeta(type):
    """元类：在类创建时扫描 path 目录，将图片文件映射为 ImageRef 属性。"""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if name == "ImageDir":
            return cls
        cls_path = namespace.get("path", "")
        if cls_path:
            cls._discover(cls_path)
        return cls

    def _discover(cls, dir_path: str) -> None:
        base = Path(dir_path)
        if not base.is_dir():
            return
        for f in sorted(base.iterdir()):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp"):
                attr = f.stem
                if not hasattr(cls, attr):
                    setattr(cls, attr, ImageRef(f))


class ImageDir(metaclass=ImageDirMeta):
    """声明式参考图管理器。

    用法1 — 子类声明（推荐）:
        class StoreImages(ImageDir):
            path = "images/store"

        # StoreImages.store_icon  → ImageRef("images/store/store_icon.png")

    用法2 — 直接实例化:
        store = ImageDir("images/store")
        # store.store_icon  → ImageRef("images/store/store_icon.png")
    """

    path: str = ""

    def __init__(self, path: str = "") -> None:
        if path:
            object.__setattr__(self, "path", path)
            self.__class__._discover(path)

    @classmethod
    def list_all(cls) -> list[ImageRef]:
        """列出目录下所有参考图。"""
        return [v for v in vars(cls).values() if isinstance(v, ImageRef)]

    @classmethod
    def validate(cls) -> list[str]:
        """检查所有已映射的参考图文件是否存在，返回缺失列表。"""
        missing: list[str] = []
        for _name, ref in vars(cls).items():
            if isinstance(ref, ImageRef) and not ref.path.exists():
                missing.append(str(ref.path))
        return missing
