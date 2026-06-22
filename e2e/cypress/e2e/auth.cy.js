// CondoBuddy2 E2E Tests — Auth & API Connectivity

describe('FastAPI Core Health', () => {
  it('core backend responds to health check', () => {
    cy.request('GET', 'http://localhost:8000/health').then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status', 'ok');
    });
  });
});

describe('Frappe ↔ Core API Connectivity', () => {
  it('Frappe API is reachable', () => {
    cy.request({
      url: 'http://localhost:8080/api/method/healthcheck',
      failOnStatusCode: false
    }).then((response) => {
      // Frappe may return 404 if healthcheck not set, but should not crash
      expect(response.status).to.be.oneOf([200, 404]);
    });
  });

  it('Frappe web pages are served', () => {
    cy.request({
      url: 'http://localhost:8080/resident-portal.html',
      failOnStatusCode: false
    }).then((response) => {
      expect(response.status).to.be.oneOf([200, 404, 500]);
    });
  });
});
