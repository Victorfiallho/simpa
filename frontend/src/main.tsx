import '@fontsource-variable/inter';
import './estilos/global.css';

import { LazyMotion, MotionConfig } from 'motion/react';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './App';
import { ProvedorDeSessao } from './sessao';

const carregarRecursosDeMovimento = () => import('./recursosDeMovimento').then((m) => m.default);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* LazyMotion com componentes `m`: os recursos de animação chegam num arquivo à parte, depois
        da primeira tela; até lá os componentes já aparecem no estado final. */}
    <LazyMotion features={carregarRecursosDeMovimento} strict>
      <MotionConfig reducedMotion="user">
        <ProvedorDeSessao>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ProvedorDeSessao>
      </MotionConfig>
    </LazyMotion>
  </StrictMode>,
);
