import {createRoot} from 'react-dom/client';
import {App} from './App';
import '@fontsource-variable/inter';
import './styles.css';
import './theme.css';

createRoot(document.getElementById('root')!).render(<App />);
