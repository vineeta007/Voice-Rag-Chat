import { useEffect, useState } from 'react';
import './ThemeToggle.css';

export type Theme = 'light' | 'dark';

interface ThemeToggleProps {
    onThemeChange?: (theme: Theme) => void;
}

export function ThemeToggle({ onThemeChange }: ThemeToggleProps) {
    const [theme, setTheme] = useState<Theme>('light');
    const [mounted, setMounted] = useState(false);

    // Initialize theme on mount - respect localStorage and system preference
    useEffect(() => {
        const savedTheme = localStorage.getItem('theme') as Theme | null;
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        let initialTheme: Theme;
        if (savedTheme) {
            // Use saved preference
            initialTheme = savedTheme;
        } else if (prefersDark) {
            // Use system preference
            initialTheme = 'dark';
        } else {
            // Default to light
            initialTheme = 'light';
        }

        setTheme(initialTheme);
        applyTheme(initialTheme);
        setMounted(true);
    }, []);

    // Apply theme to document
    const applyTheme = (newTheme: Theme) => {
        const root = document.documentElement;
        root.setAttribute('data-theme', newTheme);
        root.style.colorScheme = newTheme;

        // Save to localStorage
        localStorage.setItem('theme', newTheme);

        if (onThemeChange) {
            onThemeChange(newTheme);
        }
    };

    // Toggle theme
    const handleToggle = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
        applyTheme(newTheme);
    };

    // Don't render until mounted to avoid hydration mismatch
    if (!mounted) {
        return null;
    }

    return (
        <button
            className={`theme-toggle ${theme}`}
            onClick={handleToggle}
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode (${theme === 'light' ? '🌙' : '☀️'})`}
        >
            <div className="toggle-track">
                <div className="toggle-thumb">
                    <span className="theme-icon">
                        {theme === 'light' ? '☀️' : '🌙'}
                    </span>
                </div>
            </div>
        </button>
    );
}
