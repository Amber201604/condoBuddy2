// CondoBuddy2 E2E Tests — Resident Portal

describe('Resident Portal', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('loads the resident portal page', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-brand').should('contain', 'CondoBuddy');
    cy.get('.cb-brand-text small').should('contain', 'Resident Portal');
  });

  it('has bottom navigation with all resident sections', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tabbar').should('be.visible');
    cy.get('.cb-tab').should('have.length', 5);
    cy.get('.cb-tab').contains('Home').should('be.visible');
    cy.get('.cb-tab').contains('Visitors').should('be.visible');
    cy.get('.cb-tab').contains('Packages').should('be.visible');
    cy.get('.cb-tab').contains('Book').should('be.visible');
    cy.get('.cb-tab').contains('Access').should('be.visible');
  });

  it('does not expose management-only CCTV to residents', () => {
    cy.visit('/resident-portal.html');
    cy.get('#cctv').should('not.exist');
  });

  it('switches between sections on tab click', () => {
    cy.visit('/resident-portal.html');

    cy.get('.cb-tab').contains('Book').click();
    cy.get('#bookings').should('have.class', 'is-active');
    cy.get('#bookings').should('contain', 'Facility Booking');

    cy.get('.cb-tab').contains('Visitors').click();
    cy.get('#visitors').should('have.class', 'is-active');
    cy.get('#visitors').should('contain', 'Pre-register a Visitor');
  });

  it('booking form has required fields', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Book').click();

    cy.get('#booking-form').should('be.visible');
    cy.get('#booking-facility').should('exist');
    cy.get('#booking-date').should('have.attr', 'required');
    cy.get('#booking-start').should('have.attr', 'required');
    cy.get('#booking-end').should('have.attr', 'required');
  });

  it('visitor form has required fields', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Visitors').click();

    cy.get('#visitor-form').should('be.visible');
    cy.get('#visitor-name').should('have.attr', 'required');
    cy.get('#visitor-type').should('exist');
  });

  it('portal is responsive on mobile viewport', () => {
    cy.viewport(375, 667); // iPhone SE
    cy.visit('/resident-portal.html');
    cy.get('.cb-portal').should('be.visible');
    cy.get('.cb-tabbar').should('be.visible');
    cy.get('.cb-brand').should('be.visible');
  });
});

describe('Frappe Desk Login', () => {
  it('shows Frappe login page', () => {
    cy.visit('/login');
    cy.get('body').should('contain', 'Login');
  });
});
