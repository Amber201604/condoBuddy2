// CondoBuddy2 E2E Tests — Facility Booking Flow

describe('Facility Booking Flow', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('facility booking page loads with form', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Book').click();

    cy.get('#booking-form').should('be.visible');
    cy.get('#booking-facility').should('exist');
    cy.get('#booking-date').should('exist');
    cy.get('#booking-start').should('exist');
    cy.get('#booking-end').should('exist');
    cy.get('#booking-form button[type="submit"]').should('contain', 'Request Booking');
  });

  it('submits booking form (mocked)', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Book').click();

    // Intercept the booking API method
    cy.intercept('POST', '**/api/method/condobuddy2_erp.api.api.create_booking', {
      statusCode: 200,
      body: { message: { booking_id: 'FB-2026-00001', status: 'Pending' } }
    }).as('createBooking');

    cy.get('#booking-facility').then(($sel) => {
      // Inject an option so the select has a value during the mocked test.
      $sel.append('<option value="FAC-Test">Test Room</option>');
    });
    cy.get('#booking-facility').select('FAC-Test');
    cy.get('#booking-date').type('2026-06-25');
    cy.get('#booking-start').type('10:00');
    cy.get('#booking-end').type('11:00');
    cy.get('#booking-purpose').type('Team meeting');

    cy.get('#booking-form button[type="submit"]').click();

    cy.wait('@createBooking').its('response.statusCode').should('eq', 200);
  });

  it('shows booking history section', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Book').click();
    cy.get('#booking-history').should('exist');
  });
});

describe('Visitor Registration Flow', () => {
  it('visitor form submits successfully (mocked)', () => {
    cy.visit('/resident-portal.html');
    cy.get('.cb-tab').contains('Visitors').click();

    cy.intercept('POST', '**/api/method/condobuddy2_erp.api.api.create_visitor', {
      statusCode: 200,
      body: { message: { visitor_id: 'VIS-2026-00001', visitor_name: 'John Doe', qr_code: 'abc123', status: 'Pre-registered' } }
    }).as('createVisitor');

    cy.get('#visitor-name').type('John Doe');
    cy.get('#visitor-phone').type('555-0100');
    cy.get('#visitor-type').select('Guest');

    cy.get('#visitor-form button[type="submit"]').click();

    cy.wait('@createVisitor').its('response.statusCode').should('eq', 200);
    // Access pass modal appears after registration
    cy.get('#cb-modal').should('be.visible');
    cy.get('.cb-pass-code').should('contain', 'abc123');
  });
});
