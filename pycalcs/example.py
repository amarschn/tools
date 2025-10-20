# Save this file as /pycalcs/example.py

def calculate_example(param1, param2, param3):
    """
    Calculates an example product and quotient.

    This function demonstrates the docstring and return
    structure for a standalone example tool. The UI will
    dynamically parse this docstring to build itself.

    ---Parameters---
    param1 : float
        The first input (P1), used for multiplication. Blah Blah Blah.
    param2 : float
        The second input (P2), also used for multiplication.
    param3 : float
        The third input (P3), used for division.

    ---Returns---
    product : float
        The product of P1 and P2.
    quotient : float
        The quotient of P3 and 100.

    ---LaTeX---
    R_p = P_1 \\times P_2
    R_q = \\frac{P_3}{100}
    """
    try:
        p1 = float(param1)
        p2 = float(param2)
        p3 = float(param3)
        
        res_p = p1 * p2
        res_q = p3 / 100
        
        # Return a dictionary.
        # The keys 'product' and 'quotient' MUST match the
        # keys used in the '---Returns---' section.
        return {
            'product': res_p,
            'quotient': res_q,
            'subst_product': f'R_p = {p1} \\times {p2} = {res_p:.2f}',
            'subst_quotient': f'R_q = \\frac{{{p3}}}{{100}} = {res_q:.2f}'
        }
    except Exception as e:
        # Pass the error back to JavaScript
        return {'error': str(e)}