import * as React from "react";
import classnames from "classnames";
import type { LucideIcon } from "lucide-react";
import {
    ArrowLeft,
    ArrowRight,
    Ban,
    Bug,
    Check,
    ChevronDown,
    ChevronRight,
    ChevronsDown,
    CircleHelp,
    CircleOff,
    CircleX,
    Clipboard,
    CopyPlus,
    Download,
    ExternalLink,
    Files,
    FolderOpen,
    Forward,
    Globe,
    History,
    Info,
    LoaderCircle,
    Paintbrush,
    Pause,
    Pencil,
    Play,
    Plus,
    RefreshCw,
    RotateCcw,
    Save,
    Search,
    Settings,
    Square,
    SquareCheck,
    SquarePlus,
    Tag,
    Terminal,
    Trash2,
    TriangleAlert,
    Upload,
    X,
} from "lucide-react";

export type IconName =
    "arrow-left"
    | "arrow-right"
    | "ban"
    | "bug"
    | "check"
    | "chevron-down"
    | "chevron-right"
    | "chevrons-down"
    | "circle-off"
    | "clipboard"
    | "close"
    | "close-circle"
    | "copy-plus"
    | "download"
    | "external-link"
    | "files"
    | "folder-open"
    | "forward"
    | "globe"
    | "help"
    | "history"
    | "info"
    | "loading"
    | "palette"
    | "pause"
    | "pencil"
    | "play"
    | "plus"
    | "refresh"
    | "replay"
    | "save"
    | "search"
    | "settings"
    | "square"
    | "square-check"
    | "square-plus"
    | "tag"
    | "terminal"
    | "trash"
    | "upload"
    | "warning";

const icons: Record<IconName, LucideIcon> = {
    "arrow-left": ArrowLeft,
    "arrow-right": ArrowRight,
    ban: Ban,
    bug: Bug,
    check: Check,
    "chevron-down": ChevronDown,
    "chevron-right": ChevronRight,
    "chevrons-down": ChevronsDown,
    "circle-off": CircleOff,
    clipboard: Clipboard,
    close: X,
    "close-circle": CircleX,
    "copy-plus": CopyPlus,
    download: Download,
    "external-link": ExternalLink,
    files: Files,
    "folder-open": FolderOpen,
    forward: Forward,
    globe: Globe,
    help: CircleHelp,
    history: History,
    info: Info,
    loading: LoaderCircle,
    palette: Paintbrush,
    pause: Pause,
    pencil: Pencil,
    play: Play,
    plus: Plus,
    refresh: RefreshCw,
    replay: RotateCcw,
    save: Save,
    search: Search,
    settings: Settings,
    square: Square,
    "square-check": SquareCheck,
    "square-plus": SquarePlus,
    tag: Tag,
    terminal: Terminal,
    trash: Trash2,
    upload: Upload,
    warning: TriangleAlert,
};

type IconProps = Omit<React.ComponentPropsWithoutRef<"svg">, "name"> & {
    name: IconName;
    fixedWidth?: boolean;
    spin?: boolean;
};

export default function Icon({
    name,
    className,
    fixedWidth = false,
    spin = false,
    ...props
}: IconProps) {
    const SvgIcon = icons[name];
    return (
        <SvgIcon
            className={classnames(
                "icon",
                `icon-${name}`,
                {
                    "icon-fw": fixedWidth,
                    "icon-spin": spin,
                },
                className,
            )}
            size={16}
            strokeWidth={2}
            aria-hidden="true"
            focusable="false"
            {...props}
        />
    );
}
