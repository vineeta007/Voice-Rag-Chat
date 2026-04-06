import './SkeletonLoader.css';

interface SkeletonLoaderProps {
    /**
     * Number of skeleton lines to show (default: 3)
     * Each line represents content being loaded
     */
    lines?: number;
    /**
     * Whether to show a longer final line (like paragraph end)
     */
    hasShortLine?: boolean;
}

export function SkeletonLoader({ lines = 3, hasShortLine = true }: SkeletonLoaderProps) {
    return (
        <div className="skeleton-loader">
            {/* Skeleton lines that mimic message content */}
            {Array.from({ length: lines }).map((_, index) => (
                <div
                    key={`skeleton-line-${index}`}
                    className={`skeleton-line ${index === lines - 1 && hasShortLine ? 'skeleton-line-short' : ''}`}
                    style={{
                        animationDelay: `${index * 0.1}s`
                    }}
                />
            ))}
        </div>
    );
}
