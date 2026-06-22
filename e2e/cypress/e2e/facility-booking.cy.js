// CondoBuddy2 E2E Tests — Facility Booking Flow

describe('Facility Booking Flow', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('facility booking page loads with form', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Bookings').click();
    
    cy.get('#booking-form').should('be.visible');
    cy.get('#booking-facility').should('exist');
    cy.get('#booking-date').should('exist');
    cy.get('#booking-start').should('exist');
    cy.get('#booking-end').should('exist');
    cy.get('button[type="submit"]').should('contain', 'Book Now');
  });

  it('submits booking form (mocked)', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Bookings').click();
    
    // Intercept the API call
    cy.intercept('POST', '**/api/resource/Facility Booking', {
      statusCode: 200,
      body: { data: { name: 'FB-2026-00001' } }
    }).as('createBooking');
    
    cy.get('#booking-facility').select(0);
    cy.get('#booking-date').type('2026-06-25');
    cy.get('#booking-start').type('10:00');
    cy.get('#booking-end').type('11:00');
    cy.get('#booking-purpose').type('Team meeting');
    
    cy.get('button[type="submit"]').click();
    
    cy.wait('@createBooking').its('response.statusCode').should('eq', 200);
  });

  it('shows booking history section', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Bookings').click();
    cy.get('#booking-history').should('exist');
  });
});

describe('Visitor Registration Flow', () => {
  it('visitor form submits successfully (mocked)', () => {
    cy.visit('/resident-portal.html');
    cy.contains('Visitors').click();
    
    cy.intercept('POST', '**/api/method/condobuddy2_erp.api.api.create_visitor', {
      statusCode: 200,
      body: { message: { visitor_id: 'VIS-2026-00001', qr_code: 'abc123' } }
    }).as('createVisitor');
    
    cy.get('#visitor-name').type('John Doe');
    cy.get('#visitor-phone').type('555-0100');
    cy.get('#visitor-type').select('Guest');
    
    cy.get('button[type="submit"]').click();
    
    cy.wait('@createVisitor').its('response.statusCode').should('eq', 200);
  });
});
