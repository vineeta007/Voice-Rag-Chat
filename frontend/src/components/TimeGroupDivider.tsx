import './TimeGroupDivider.css';

interface TimeGroupDividerProps {
    label: string;
}

export function TimeGroupDivider({ label }: TimeGroupDividerProps) {
    return (
        <div className="time-group-divider">
            <div className="divider-line"></div>
            <div className="divider-label">{label}</div>
            <div className="divider-line"></div>
        </div>
    );
}
