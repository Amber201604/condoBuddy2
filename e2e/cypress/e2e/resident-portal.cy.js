// CondoBuddy2 E2E Tests — Resident Portal

describe('Resident Portal', () => {
  beforeEach(() => {
    // Clear cookies and localStorage before each test
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('loads the resident portal page', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-header h1').should('contain', 'CondoBuddy2');
    cy.get('.cb-subtitle').should('contain', 'Resident Portal');
  });

  it('has navigation with all sections', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-nav').should('be.visible');
    cy.get('.cb-nav-item').should('have.length.at.least', 5);
    cy.contains('Dashboard').should('be.visible');
    cy.contains('Bookings').should('be.visible');
    cy.contains('Visitors').should('be.visible');
    cy.contains('Packages').should('be.visible');
    cy.contains('Access').should('be.visible');
    cy.contains('CCTV').should('be.visible');
  });

  it('switches between sections on nav click', () => {
    cy.visit('/resident-portal.html');
    
    // Click Bookings
    cy.contains('Bookings').click();
    cy.get('#bookings').should('have.class', 'active');
    cy.get('#bookings').should('contain', 'Facility Booking');
    
    // Click Visitors
    cy.contains('Visitors').click();
    cy.get('#visitors').should('have.class', 'active');
    cy.get('#visitors').should('contain', 'Pre-register Visitor');
    
    // Click CCTV
    cy.contains('CCTV').click();
    cy.get('#cctv').should('have.class', 'active');
    cy.get('#cctv').should('contain', 'CCTV Feeds');
  });

  it('booking form has required fields', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Bookings').click();
    
    cy.get('#booking-form').should('be.visible');
    cy.get('#booking-facility').should('exist');
    cy.get('#booking-date').should('have.attr', 'required');
    cy.get('#booking-start').should('have.attr', 'required');
    cy.get('#booking-end').should('have.attr', 'required');
  });

  it('visitor form has required fields', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Visitors').click();
    
    cy.get('#visitor-form').should('be.visible');
    cy.get('#visitor-name').should('have.attr', 'required');
    cy.get('#visitor-type').should('exist');
  });

  it('portal is responsive on mobile viewport', () => {
    cy.viewport(375, 667); // iPhone SE
    cy.visit('/resident-portal.html');
    cy.get('.cb-portal').should('be.visible');
    cy.get('.cb-nav').should('be.visible');
    cy.get('.cb-header h1').should('be.visible');
  });
});

describe('Frappe Desk Login', () => {
  it('shows Frappe login page', () => {
    cy.visit('/login');
    cy.get('body').should('contain', 'Login');
  });
});
