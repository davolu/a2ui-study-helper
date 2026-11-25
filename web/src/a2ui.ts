/**
 * Everything A2UI on the browser side, in one small file.
 *
 *  - MessageProcessor (from @a2ui/web_core): reads the agent's A2UI messages
 *    and keeps the state of every surface (its components and its data).
 *  - basicCatalog: the A2UI v1.0 basic components (Text, Card, Button, ...).
 *    The browser knows how to draw these. The agent may ONLY use these.
 */
import {MessageProcessor, type ActionPayload, type SurfaceModel} from '@a2ui/web_core/v1_0';
import {basicCatalog} from '@a2ui/web_core/catalogs/basic/v1';
import type {ReactCatalogComponent} from '@a2ui/react';

export type A2uiMessage = Record<string, unknown>;

export class StudySurfaces {
  readonly processor: MessageProcessor<ReactCatalogComponent>;

  constructor(onAction: (action: ActionPayload) => void) {
    // When the student presses a Button, the processor calls onAction with
    // the event name and its context (e.g. the answers they picked).
    this.processor = new MessageProcessor<ReactCatalogComponent>([basicCatalog], onAction);
  }

  /** Apply the agent's messages: create surfaces, add components, fill data. */
  apply(messages: A2uiMessage[]): string[] {
    const problems: string[] = [];
    for (const error of this.processor.processMessagesWithErrors(messages)) {
      problems.push(error.error.message);
    }
    return problems;
  }

  /** Tell the agent which catalogs this browser can draw (sent with every request). */
  capabilities() {
    return this.processor.getRendererCapabilities({versions: ['1.0']});
  }

  surface(id: string): SurfaceModel<ReactCatalogComponent> | undefined {
    return this.processor.getSurface(id);
  }
}

/** A button press, as an A2UI v1.0 "renderer to agent" message. */
export function actionMessage(action: ActionPayload) {
  return {
    version: '1.0',
    action: {
      name: action.name,
      surfaceId: action.surfaceId,
      sourceComponentId: action.sourceComponentId,
      timestamp: action.timestamp || new Date().toISOString(),
      context: action.context ?? {},
    },
  };
}
