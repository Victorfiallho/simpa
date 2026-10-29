import '@fontsource-variable/inter';
import './estilos/global.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';
import { ProvedorDeSessao } from './sessao';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProvedorDeSessao>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ProvedorDeSessao>
  </StrictMode>,
);
